from django.db import models
from django.contrib.auth.models import AbstractUser
from .emojis import CATEGORY_EMOJI_CHOICES

# 1. جدول المحافظات النهائي
class Governorate(models.Model):
    name_ar = models.CharField(max_length=100, verbose_name="المحافظة بالكامل (عربي)")
    name_en = models.CharField(max_length=100, verbose_name="المحافظة بالكامل (إنجليزي)")

    def __str__(self):
        return self.name_ar

# 2. جدول المدن والمراكز النهائي
class City(models.Model):
    governorate = models.ForeignKey(Governorate, on_delete=models.CASCADE, related_name='cities', verbose_name="المحافظة")
    name_ar = models.CharField(max_length=100, verbose_name="المدينة / المركز (عربي)")
    name_en = models.CharField(max_length=100, verbose_name="المدينة / المركز (إنجليزي)")

    def __str__(self):
        return f"{self.name_ar} - {self.governorate.name_ar}"

# 🌟 كلاس الأقسام المطور والديناميكي بالكامل لدعم الأقسام الرئيسية والفرعية والتخصصات (نسخة الإيموجيات المنسدلة) 🌟
class Category(models.Model):
    name_ar = models.CharField(max_length=100, verbose_name="اسم القسم/التخصص بالعربية")
    name_en = models.CharField(max_length=100, verbose_name="اسم القسم/التخصص بالإنجليزية", blank=True, null=True)
    
    # 🌟 الحقل السحري: إذا كان فارغاً فهو قسم رئيسي، وإذا كان مرتبطاً بقسم فهو فرعي أو تخصص
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='children', 
        verbose_name="القسم الأب (اتركه فارغاً ليكون قسماً رئيسياً)"
    )
    
    # 🚀 تحديث الحقل ليقرأ أوتوماتيكياً من مكتبة الإيموجيات الخارجية كقائمة خيارات منسدلة فخمة 🚀
    icon_emoji = models.CharField(
        max_length=10, 
        choices=CATEGORY_EMOJI_CHOICES, # ربط القائمة المنسدلة الذكية
        default="🛠️", 
        verbose_name="أيقونة التخصص (إيموجي)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "الالقسم والتخصص"
        verbose_name_plural = "الأقسام والتخصصات"

    # دالة ذكية تعرض مسار القسم بالكامل في لوحة التحكم (مثال: خدمات منزلية -> سباكة -> تمديد شبكات)
    def __str__(self):
        full_path = [f"{self.icon_emoji} {self.name_ar}"] # 🌟 دمج الإيموجي في أول المسار ليعطي مظهراً فخماً بداخل لوحة الإدارة
        k = self.parent
        while k is not None:
            full_path.append(k.name_ar)
            k = k.parent
        return " -> ".join(reversed(full_path))


# 3. جدول المستخدم النهائي والمستقر
class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('client', 'طالب خدمة'),
        ('provider', 'مقدم خدمة'),
    )
    
    VERIFICATION_STATUS_CHOICES = (
        ('not_submitted', 'لم يتم تقديم الطلب'),
        ('pending', 'قيد المراجعة والتدقيق'),
        ('verified', 'حساب موثق ومؤكد'),
        ('rejected', 'تم رفض الطلب'),
    )

    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True, verbose_name="رقم الهاتف")
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='client', verbose_name="نوع الحساب")
    
    # ربط المستخدم بجداول الموقع الجغرافي بشكل احترافي ومفتوح
    governorate = models.ForeignKey(Governorate, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="المحافظة")
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="المدينة / المركز")
    address_details = models.CharField(max_length=255, blank=True, null=True, verbose_name="تفاصيل العنوان (الشارع / الحي)")

    # بيانات التوثيق
    national_id = models.CharField(max_length=14, blank=True, null=True, verbose_name="الرقم القومي (14 رقم)")
    id_front_image = models.ImageField(upload_to='national_ids/front/', blank=True, null=True, verbose_name="صورة وجه البطاقة")
    id_back_image = models.ImageField(upload_to='national_ids/back/', blank=True, null=True, verbose_name="صورة ظهر البطاقة")
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='not_submitted', verbose_name="حالة التوثيق")
    # أضف هذا السطر داخل حقول كلاس الـ User
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="المهنة / التخصص")
    # أضف هذا الحقل داخل كلاس User في ملف models.py
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True, default='profile_pics/default_user.png', verbose_name="صورة الحساب")
    # الحقول الجديدة لربط التخصصات والاهتمامات الديناميكية الشجرية
        # 🚀 حقول التوزيع الجغرافي والإتاحة اللحظية لايف للسوبر آب 🚀
    is_active_now = models.BooleanField(default=False, verbose_name="متاح الآن للعمل")
    latitude = models.FloatField(null=True, blank=True, verbose_name="خط العرض GPS")
    longitude = models.FloatField(null=True, blank=True, verbose_name="خط الطول GPS")
    last_location_update = models.DateTimeField(null=True, blank=True, verbose_name="آخر تحديث للموقع")

    category = models.ForeignKey(
        'Category', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='providers', 
        verbose_name="التخصص المهني الرئيسي (للفنيين فقط)"
    )
    
    interests = models.ManyToManyField(
        'Category', 
        blank=True, 
        related_name='interested_users', 
        verbose_name="الاهتمامات والاحتياجات (لطالبي الخدمة فقط)"
    )


    @property
    def is_verified_provider(self):
        return self.user_type == 'provider' and self.verification_status == 'verified'

    def __str__(self):
        return f"{self.username} - {self.get_user_type_display()}"

    # أضف هذه الدالة داخل كلاس الـ User في ملف models.py
    @property
    def get_average_rating(self):
        """دالة لحساب متوسط تقييم النجوم لمقدم الخدمة تلقائياً"""
        ratings = self.received_ratings.all()
        if ratings.exists():
            total_stars = sum(r.stars for r in ratings)
            avg = total_stars / ratings.count()
            return round(avg, 1) # تقريب للرقم مثل 4.5
        return 0.0

        # 🔐 دالة التشفير الذكي لأرقام الهواتف (تحافظ على أول 3 أرقام وآخر 3 أرقام وتخفي المنتصف) 🔐
    @property
    def masked_phone(self):
        if self.phone_number and len(self.phone_number) >= 8:
            # مثال: 01012345678 يتحول إلى 010*****678
            return f"{self.phone_number[:3]}*****{self.phone_number[-3:]}"
        return self.phone_number

# أضف هذا الجدول في نهاية ملف models.py
# 🌟 كلاس المنشورات المطور (يدعم الصور، الفيديوهات القصيرة، والدوال الإحصائية الذكية) 🌟
class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts', verbose_name="كاتب المنشور")
    content = models.TextField(verbose_name="ماذا يدور في ذهنك؟")
    image = models.ImageField(upload_to='posts_images/', blank=True, null=True, verbose_name="صورة المنشور")
    
    # 🎬 الحقل السحري: دعم رفع الفيديوهات القصيرة حتى دقيقة 🎬
    video = models.FileField(upload_to='post_videos/', blank=True, null=True, verbose_name="فيديو المنشور")

    # ربط المنشور بقسم معين لفلترته حسب اهتمامات المستخدمين (🔧، 👨‍💻، 🍔، 🚖)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="قسم الاهتمام")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ النشر")

    class Meta:
        verbose_name = "المنشور"
        verbose_name_plural = "المنشورات"
        ordering = ['-created_at'] # ترتيب المنشورات من الأحدث للأقدم تلقائياً بالتايم لاين

    # 🚀 دالة ذكية 1: جلب التعليقات الرئيسية فقط (التي ليس لها أب) لترتيب العروض بنظافة
    def get_main_comments(self):
        return self.comments.filter(parent=None).order_by('-created_at')

    # 🚀 دالة ذكية 2: فحص سريع لمعرفة هل المنشور يحتوي على فيديو مرفق أم لا لتغيير أيقونة العرض
    def has_video(self):
        return bool(self.video)

    def __str__(self):
        return f"منشور بواسطة {self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    # 🚀 التحديث السحري: إجبار الموديل على قراءة الأعداد الحية من جدول الـ PostAction عند الريفريش 🚀
    @property
    def likes_count(self):
        # استدعاء جدول PostAction وفلترته لحساب الإعجابات الحقيقية للمنشور الحالي
        from .models import PostAction  # استيراد داخلي لمنع التداخل (Circular Import)
        return PostAction.objects.filter(post=self, action_type='like').count()

    @property
    def dislikes_count(self):
        # استدعاء جدول PostAction وفلترته لحساب الرفض الحقيقي للمنشور الحالي
        from .models import PostAction
        return PostAction.objects.filter(post=self, action_type='dislike').count()



    class Meta:
        ordering = ['-created_at'] # المنشورات الأحدث تظهر أولاً دائماً مثل فيسبوك

    def __str__(self):
        return f"منشور بواسطة {self.user.username} - {self.created_at.strftime('%Y-%m-%d')}"

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name="المنشور")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="كاتب التعليق")
    content = models.TextField(verbose_name="التعليق")
    
    # حقل الربط السحري: لكي يقبل التعليق أن يكون ردًا على تعليق آخر
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies', verbose_name="التعليق الأب")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at'] # الردود الأقدم أولاً لترتيب سياق النقاش

    def __str__(self):
        return f"تعليق من {self.user.username} على بوست {self.post.id}"



class Rating(models.Model):
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_ratings')
    to_provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_ratings')
    stars = models.IntegerField(choices=[(i, i) for i in range(1, 6)], verbose_name="عدد النجوم")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_provider') # منع تكرار التقييم لنفس الشخص

    def __str__(self):
        return f"تقييم {self.stars} نجوم من {self.from_user.username} إلى {self.to_provider.username}"

# أضف هذا الجدول في نهاية ملف models.py تماماً
class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('comment', 'رد جديد على منشورك'),
        ('reply', 'رد على تعليقك'),
        ('rating', 'تقييم جديد لحسابك'),
    )
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name="المستلم")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="المرسل")
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, verbose_name="المنشور المرتبط")
    is_read = models.BooleanField(default=False, verbose_name="تمت القراءة")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at'] # الإشعارات الأحدث تظهر أولاً

    def __str__(self):
        return f"إشعار إلى {self.recipient.username} من {self.sender.username}"

# أضف هذه الجداول في نهاية ملف models.py تماماً لتوثيق العلاقات

class ChatMessage(models.Model):
    """جدول الشات والرسائل الفورية بين المستخدمين"""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    message = models.TextField(verbose_name="نص الرسالة")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at'] # ترتيب الرسائل من الأقدم للأحدث داخل المحادثة

    def __str__(self):
        return f"رسالة من {self.sender.username} إلى {self.receiver.username}"


class FriendRequest(models.Model):
    """جدول طلبات الصداقة والاتصال الاجتماعي"""
    STATUS_CHOICES = (
        ('pending', 'قيد الانتظار'),
        ('accepted', 'تم القبول (أصدقاء)'),
        ('rejected', 'تم الرفض'),
    )
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_friend_requests')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_friend_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f"طلب صداقة من {self.from_user.username} إلى {self.to_user.username} ({self.get_status_display()})"

# أضف هذا الجدول في نهاية ملف models.py تماماً لتفعيل التفاعل الحقيقي
class PostAction(models.Model):
    ACTION_CHOICES = (
        ('like', 'إعجاب'),
        ('dislike', 'عدم إعجاب'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='actions')
    action_type = models.CharField(max_length=10, choices=ACTION_CHOICES)

    class Meta:
        unique_together = ('user', 'post') # منع المستخدم من عمل أكثر من تفاعل على نفس البوست

    def __str__(self):
        return f"{self.user.username} - {self.get_action_type_display()} - بوست {self.post.id}"
