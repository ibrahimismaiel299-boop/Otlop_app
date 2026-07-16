from django import forms
from django.core.exceptions import ValidationError
from .models import User, Governorate, City, Category, Post

# 🧱 1. استمارة إنشاء حساب جديد (المسجلين والفنيين والبطاقات)
class UserSignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'كلمة المرور'}), label="كلمة المرور")
    governorate = forms.ModelChoiceField(queryset=Governorate.objects.all(), empty_label="اختر المحافظة", label="المحافظة")
    city = forms.ModelChoiceField(queryset=City.objects.all(), empty_label="اختر المدينة / المركز", label="المدينة")

    class Meta:
        model = User
        fields = [
            'username', 'password', 'phone_number', 'user_type', 
            'governorate', 'city', 'address_details', 
            'category', 'interests',  
            'national_id', 'id_front_image', 'id_back_image' 
        ]
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'اسم المستخدم'}),
            'phone_number': forms.TextInput(attrs={'placeholder': 'رقم الهاتف'}),
            'address_details': forms.TextInput(attrs={'placeholder': 'اسم الشارع، رقم العقار...'}),
            'national_id': forms.TextInput(attrs={'placeholder': 'الرقم القومي (14 رقم)'}),
            'category': forms.Select(), 
            'interests': forms.SelectMultiple(attrs={
                'style': 'width: 100%; height: 110px; padding: 8px; border-radius: 8px; background: #f7fafc;',
                'title': 'اضغط مع الاستمرار على زر Ctrl لاختيار أكثر من اهتمام'
            }), 
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


# 🧱 2. استمارة تسجيل الدخول المستقرة
class UserLoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'اسم المستخدم', 'class': 'form-control'}),
        label="اسم المستخدم"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'كلمة المرور', 'class': 'form-control'}),
        label="كلمة المرور"
    )


# 🧱 3. 🎬 استمارة المنشورات المحدثة والمحررة بالكامل من قيود الحجب (النسخة الفولاذية) 🎬
class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['content', 'image', 'video', 'category']
        widgets = {
            'content': forms.Textarea(attrs={'placeholder': 'اكتب تفاصيل طلبك أو اعرض خدماتك هنا...', 'rows': 3, 'style': 'width: 100%; border-radius: 12px; padding: 12px; border: 1px solid #ccc; outline: none; font-family: inherit;'}),
            'category': forms.Select(attrs={'style': 'padding: 10px; border-radius: 20px; border: 1px solid #ccc; outline: none; margin-top: 10px;'}),
            'video': forms.FileInput(attrs={'accept': 'video/*', 'style': 'display: none;', 'id': 'post_video_input'}),
        }

    # 🚀 الحصن البرمجي الحاسم: كسر وإلغاء إلزامية الميديا من السيرفر لفتح بوابات النشر 🚀
    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.fields['image'].required = False  # جعل الصورة اختيارية 100%
        self.fields['video'].required = False  # جعل الفيديو اختيارياً 100%
        self.fields['category'].required = False # جعل القسم اختيارياً لتفادي أي حجب صامت

    # الفحص الأمني لحجم الفيديو (يشتغل حصرياً فقط عند إرفاق ملف فعلي)
    def clean_video(self):
        video = self.cleaned_data.get('video')
        if video is not None and hasattr(video, 'size'):
            if video.size > 50 * 1024 * 1024: # حد أقصى 50 ميجا بايت
                raise ValidationError("حجم الفيديو ضخم جداً، الحد الأقصى المسموح به هو 50 ميجابايت.")
        return video

# 🧱 4. استمارة تعديل الملف الشخصي والبروفايل العام
class UserProfileForm(forms.ModelForm):
    governorate = forms.ModelChoiceField(queryset=Governorate.objects.all(), empty_label="اختر المحافظة", label="المحافظة")
    city = forms.ModelChoiceField(queryset=City.objects.all(), empty_label="اختر المدينة / المركز", label="المدينة")
    category = forms.ModelChoiceField(queryset=Category.objects.all(), required=False, empty_label="حدد المهنة (لمقدمي الخدمة فقط)", label="المهنة / التخصص")

    class Meta:
        model = User
        fields = ['profile_picture', 'phone_number', 'governorate', 'city', 'address_details', 'category']
        widgets = {
            'phone_number': forms.TextInput(attrs={'placeholder': 'رقم الهاتف الجديد'}),
            'address_details': forms.TextInput(attrs={'placeholder': 'تفاصيل العنوان السكني'}),
        }
