from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import models # استيراد هام جداً لتشغيل الـ models.Q في الشات!

# استيراد كافة الاستمارات المعتمدة
from .forms import UserSignupForm, UserLoginForm, UserProfileForm, PostForm

# استيراد كافة جداول قاعدة البيانات (تمت إضافة الموديلات الجديدة هنا بدقة لمنع التجميد)
from .models import User, Governorate, City, Category, Post, Comment, Rating, ChatMessage, FriendRequest, Notification, PostAction

def home_view(request):
    selected_gov = request.GET.get('governorate')
    selected_category = request.GET.get('category')
    
    # 1. جلب الأقسام الرئيسية فقط لتعرض كأزرار للاهتمامات بالقمة
    # جلب كافة الأقسام الرئيسية (الأب فارغ) لضمان ظهور أي قسم تنشئه من لوحة الإدارة فوراً
    category_choices = Category.objects.filter(parent=None)
    
    # جلب مقدمي الخدمات والفلترة حسب المحافظة
    providers = User.objects.filter(user_type='provider')
    if selected_gov:
        providers = providers.filter(governorate_id=selected_gov)
        
    # تهيئة استمارة المنشور وتغذيتها بكافة التخصصات والأقسام المتاحة في قاعدة البيانات ديناميكياً
    post_form = PostForm()
    if hasattr(post_form.fields, 'get'):
        if 'category' in post_form.fields:
            post_form.fields['category'].queryset = Category.objects.all()
            
    # 2. إدارة الإشعارات وطلبات الصداقة المعلقة (مرة واحدة فقط وبدون تكرار)
    unread_notifications = []
    pending_friend_requests = []
    if request.user.is_authenticated:
        unread_notifications = request.user.notifications.filter(is_read=False)
        pending_friend_requests = request.user.received_friend_requests.filter(status='pending')

    # إدارة عمليات الـ POST (إنشاء منشور أو كتابة تعليق/رد فرعي)
    if request.user.is_authenticated and request.method == 'POST':
        if 'submit_post' in request.POST:
            form = PostForm(request.POST, request.FILES)
            if form.is_valid():
                post = form.save(commit=False)
                post.user = request.user
                post.save()
                return redirect('home')
        elif 'submit_comment' in request.POST:
            post_id = request.POST.get('post_id')
            comment_content = request.POST.get('comment_content')
            parent_id = request.POST.get('parent_id')
            
            if comment_content and post_id:
                post_obj = get_object_or_404(Post, id=post_id)
                parent_obj = None
                if parent_id:
                    parent_obj = get_object_or_404(Comment, id=parent_id)
                
                Comment.objects.create(
                    post=post_obj, 
                    user=request.user, 
                    content=comment_content,
                    parent=parent_obj
                )
                
                if post_obj.user != request.user and not parent_obj:
                    from .models import Notification
                    Notification.objects.create(
                        recipient=post_obj.user,
                        sender=request.user,
                        notification_type='comment',
                        post=post_obj
                    )
                return redirect('home')

    # جلب المنشورات وترتيبها
    posts = Post.objects.all().order_by('-created_at')
    
    # 🌟 فلترة الذكاء الاصطناعي التلقائية لتايم لاين العميل بناءً على اهتماماته 🌟
    if request.user.is_authenticated and request.user.user_type == 'customer' and not selected_category:
        user_interests_ids = request.user.interests.values_list('id', flat=True)
        if user_interests_ids.exists():
            # إذا كان العميل يمتلك اهتمامات محددة مسبقاً، تظهر له بوستاتها تلقائياً فور فتح التطبيق
            posts = posts.filter(category_id__in=user_interests_ids)

    
    # 3. 🔥 محرك الفلترة الشجرية الذكي للأقسام والاحتياجات الفرعية 🔥
    if selected_category:
        category_obj = get_object_or_404(Category, id=selected_category)
        
        # جلب القسم المختار نفسه + جلب كافة معرفات الأقسام الفرعية والتخصصات المتفرعة منه عمودياً
        sub_categories_ids = [category_obj.id]
        
        # جلب المستوى الأول من الأبناء (الفرعي)
        level_1_children = category_obj.children.all()
        for child1 in level_1_children:
            sub_categories_ids.append(child1.id)
            # جلب المستوى الثاني من الأبناء (التخصصات الدقيقة)
            level_2_children = child1.children.all()
            for child2 in level_2_children:
                sub_categories_ids.append(child2.id)
                
        # الفلترة السحرية: جلب أي بوست ينتمي للقسم الرئيسي أو أي تخصص متفرع منه تلقائياً!
        posts = posts.filter(category_id__in=sub_categories_ids)
        
    # 4. فحص حالة الصداقة لكل منشور لحجب زر "إضافة صديق" ديناميكياً
    for post in posts:
        post.friend_status = None
        if request.user.is_authenticated:
            rel = FriendRequest.objects.filter(
                (models.Q(from_user=request.user) & models.Q(to_user=post.user)) |
                (models.Q(from_user=post.user) & models.Q(to_user=request.user))
            ).first()
            if rel:
                post.friend_status = rel.status

    context = {
        'providers': providers,
        'gov_choices': Governorate.objects.all(),
        'category_choices': category_choices, # إرسال الأقسام الرئيسية النظيفة فقط للفلترة العليا
        'selected_gov': int(selected_gov) if selected_gov else None,
        'selected_category': int(selected_category) if selected_category else None,
        'posts': posts,
        'post_form': post_form,
        'unread_notifications': unread_notifications,
        'pending_requests': pending_friend_requests,
    }
    return render(request, 'accounts/home.html', context)


@login_required
def delete_comment_view(request, comment_id):
    """دالة أمنية لحذف التعليق تمنح الحق فقط لصاحب المنشور أو كاتب التعليق نفسه"""
    comment = get_object_or_404(Comment, id=comment_id)
    # الشرط الصارم: يجب أن يكون المستخدم هو صاحب المنشور الرئيسي أو هو من كتب التعليق
    if request.user == comment.post.user or request.user == comment.user:
        comment.delete()
    return redirect('home')

@login_required
def add_rating_view(request):
    """دالة لاستقبال تقييم النجوم عبر نقرة سريعة من العميل وحفظها برمجياً"""
    if request.method == 'POST':
        provider_id = request.POST.get('provider_id')
        stars = request.POST.get('stars')
        if provider_id and stars:
            provider = get_object_or_404(User, id=provider_id)
            # تحديث التقييم إذا كان موجوداً مسبقاً أو إنشاء تقييم جديد (Update or Create)
            Rating.objects.update_or_create(
                from_user=request.user,
                to_provider=provider,
                defaults={'stars': int(stars)}
            )
            return JsonResponse({'status': 'success', 'avg_rating': provider.get_average_rating})
    return JsonResponse({'status': 'error'}, status=400)

# بقية الدوال (signup_view, login_view, logout_view, load_cities_view, profile_view) تظل ثابتة ومستقرة كما هي تماماً...

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home') # منع المستخدم المسجل بالفعل من دخول صفحة التسجيل
        
    if request.method == 'POST':
        form = UserSignupForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user) # تسجيل دخول تلقائي للمستخدم فور إنشاء حسابه بنجاح
            return redirect('home')
    else:
        form = UserSignupForm()
        # السر هنا: نقوم بتفريغ قائمة المدن تماماً عند تحميل الصفحة لأول مرة 
        # لكي لا تظهر كل مدن مصر دفعة واحدة، وينتظر الكود اختيار المحافظة
        form.fields['city'].queryset = City.objects.none()
        
    return render(request, 'accounts/signup.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home') # إذا كان مسجلاً بالفعل يذهب للرئيسية
        
    error_message = None
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password) # فحص الحساب مشفراً في السيرفر
            
            if user is not None:
                login(request, user) # بدء الجلسة
                return redirect('home')
            else:
                error_message = "خطأ في اسم المستخدم أو كلمة المرور! تأكد من البيانات."
    else:
        form = UserLoginForm()
        
    return render(request, 'accounts/login.html', {'form': form, 'error_message': error_message})

def logout_view(request):
    logout(request) # تدمير الجلسة ومسح الكاش من المتصفح فورا لحماية الحساب
    return redirect('home')

def load_cities_view(request):
    """دالة ذكية لاستقبال رقم المحافظة عبر AJAX وإرجاع المدن التابعة لها فقط"""
    governorate_id = request.GET.get('governorate_id')
    cities = City.objects.filter(governorate_id=governorate_id)
    
    # تحويل جينات المدن لقائمة بسيطة تحتوي على الـ ID والاسم العربي لإرسالها للمتصفح
    cities_list = list(cities.values('id', 'name_ar'))
    return JsonResponse(cities_list, safe=False)


@login_required(login_url='login')
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        # تمرير instance=user يجعل دجانجو يقوم بتحديث الحساب الحالي بدلاً من إنشاء حساب جديد
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = UserProfileForm(instance=user)
        
    return render(request, 'accounts/profile.html', {'form': form, 'user': user})

# دالة لتعليم الإشعارات كمقروءة عند فتح لوحة التنبيهات
@login_required
def mark_notifications_read_view(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success'})

# ضع هذه الدوال المصححة تماماً في نهاية ملف accounts/views.py

@login_required
def send_friend_request_view(request, user_id):
    """دالة لإرسال طلب صداقة فوري للمخدم"""
    to_user = get_object_or_404(User, id=user_id)
    if request.user != to_user:
        # منع تكرار الطلب إذا كان موجوداً مسبقاً
        FriendRequest.objects.get_or_create(from_user=request.user, to_user=to_user)
    return redirect('home')

@login_required
def accept_friend_request_view(request, request_id):
    """دالة لقبول طلب الصداقة الوارد وتغيير حالته لأصدقاء"""
    freq = get_object_or_404(FriendRequest, id=request_id, to_user=request.user)
    freq.status = 'accepted'
    freq.save()
    return redirect('home')

@login_required
def chat_rooms_list_view(request):
    """لوحة الشات الرئيسية لعرض كافة المستخدمين لبدء محادثة مغلقة"""
    users = User.objects.exclude(id=request.user.id)
    return render(request, 'accounts/chat_list.html', {'users': users})

@login_required
def chat_detail_view(request, user_id):
    """شاشة المحادثة الخاصة والمغلقة مصلحة ومؤمنة مئة بالمئة"""
    other_user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        message_text = request.POST.get('message')
        if message_text:
            ChatMessage.objects.create(sender=request.user, receiver=other_user, message=message_text)
            return redirect('chat_detail', user_id=user_id)
            
    # تم تصحيح اسم الموديل هنا بدقة لـ ChatMessage لإنهاء مشكلة التجميد
    messages = ChatMessage.objects.filter(
        (models.Q(sender=request.user) & models.Q(receiver=other_user)) |
        (models.Q(sender=other_user) & models.Q(receiver=request.user))
    )
    
    return render(request, 'accounts/chat_detail.html', {'other_user': other_user, 'chat_messages': messages})

# تحديث دالة البروفايل العام في ملف accounts/views.py لفحص حالة الصداقة وتمريرها
def public_profile_view(request, user_id):
    """عرض الملف الشخصي العام لأي فني شاملاً منشوراته وحالة الصداقة معه"""
    if request.user.is_authenticated and request.user.id == user_id:
        return redirect('profile')
        
    target_user = get_object_or_404(User, id=user_id)
    user_posts = Post.objects.filter(user=target_user)
    
    # 💡 فحص حالة الصداقة برمجياً بين الزائر وصاحب البروفايل 💡
    friend_status = None
    if request.user.is_authenticated:
        rel = FriendRequest.objects.filter(
            (models.Q(from_user=request.user) & models.Q(to_user=target_user)) |
            (models.Q(from_user=target_user) & models.Q(to_user=request.user))
        ).first()
        if rel:
            friend_status = rel.status # ستكون 'pending' أو 'accepted'
            
    return render(request, 'accounts/public_profile.html', {
        'target_user': target_user,
        'user_posts': user_posts,
        'friend_status': friend_status # تمرير الحالة لزر الواجهة الأمامية
    })

# أضف هذه الدالة في نهاية ملف views.py للتحكم في الإعجابات
@login_required
def post_action_view(request, post_id, action_type):
    """دالة تفاعلية لاستقبال الإعجابات وعدم الإعجابات وتحديث العدادات فوراً"""
    post_obj = get_object_or_404(Post, id=post_id)
    if action_type in ['like', 'dislike']:
        # إذا كان المستخدم ضغط على نفس الزر سابقاً، نقوم بإلغاء التفاعل (Toggle)
        existing_action = PostAction.objects.filter(user=request.user, post=post_obj).first()
        if existing_action:
            if existing_action.action_type == action_type:
                existing_action.delete()
            else:
                existing_action.action_type = action_type
                existing_action.save()
        else:
            PostAction.objects.create(user=request.user, post=post_obj, action_type=action_type)
            
    return JsonResponse({
        'status': 'success',
        'likes': post_obj.likes_count,
        'dislikes': post_obj.dislikes_count
    })

# أضف هذه الدوال في نهاية ملف views.py للتشغيل اللحظي

@login_required
def check_live_updates_view(request):
    """دالة ذكية تفحص وجود إشعارات أو طلبات صداقة جديدة كل بضع ثوانٍ خلف الكواليس"""
    unread_notifs = request.user.notifications.filter(is_read=False)
    pending_reqs = request.user.received_friend_requests.filter(status='pending')
    
    # تحويل البيانات لصيغة بسيطة يفهمها الجافا سكريبت
    notifs_data = [{'id': n.id, 'text': f"{n.sender.username} {n.get_notification_type_display()}"} for n in unread_notifs]
    reqs_data = [{'id': r.id, 'sender': r.from_user.username} for r in pending_reqs]
    
    return JsonResponse({
        'unread_count': unread_notifs.count(),
        'notifications': notifs_data,
        'pending_requests': reqs_data
    })

@login_required
def check_new_messages_view(request, user_id):
    """دالة تفحص وجود رسائل شات جديدة بينك وبين الشخص اللي فاتح محادثته حالياً"""
    other_user = get_object_or_404(User, id=user_id)
    # جلب الرسائل غير المقروءة المرسلة من الطرف الآخر لك
    new_msgs = ChatMessage.objects.filter(sender=other_user, receiver=request.user, is_read=False)
    
    msgs_data = [{'id': m.id, 'message': m.message} for m in new_msgs]
    # تعليم الرسائل كمقروءة فور جلبها للشاشة
    new_msgs.update(is_read=True)
    
    return JsonResponse({'new_messages': msgs_data})

@login_required
def reject_friend_request_view(request, request_id):
    """دالة لرفض طلب الصداقة وحذفه لبيئة نظيفة"""
    freq = get_object_or_404(FriendRequest, id=request_id, to_user=request.user)
    freq.delete() # حذف الطلب تماماً عند الرفض
    return redirect('home')

# أضف هذه الدوال في نهاية ملف views.py لتشغيل عداد الشات وقائمة الأصدقاء

@login_required
def check_unread_messages_count_view(request):
    """دالة تحسب إجمالي الرسائل غير المقروءة الواردة للمستخدم لعرضها فوق أيقونة الشات"""
    count = ChatMessage.objects.filter(receiver=request.user, is_read=False).count()
    return JsonResponse({'unread_messages_count': count})

@login_required
def friends_list_view(request):
    """دالة لجلب وعرض قائمة الأصدقاء الحاليين للمستخدم (الطلبات المقبولة)"""
    # جلب الطلبات المقبولة سواء كان المستخدم هو المرسل أو المستقبل
    friends_relations = FriendRequest.objects.filter(
        (models.Q(from_user=request.user) | models.Q(to_user=request.user)) & 
        models.Q(status='accepted')
    )
    
    # استخراج حسابات الأصدقاء الفعليين من العلاقات
    friends = []
    for rel in friends_relations:
        if rel.from_user == request.user:
            friends.append(rel.to_user)
        else:
            friends.append(rel.from_user)
            
    return render(request, 'accounts/friends_list.html', {'friends': friends})
