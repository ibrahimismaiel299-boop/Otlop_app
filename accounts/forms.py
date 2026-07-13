from django import forms
from .models import User, Governorate, City

class UserSignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'كلمة المرور'}), label="كلمة المرور")
    governorate = forms.ModelChoiceField(queryset=Governorate.objects.all(), empty_label="اختر المحافظة", label="المحافظة")
    city = forms.ModelChoiceField(queryset=City.objects.all(), empty_label="اختر المدينة / المركز", label="المدينة")

    class Meta:
        model = User
        # 🌟 دمج كافة الحقول الأساسية والأمنية مع التخصص والاهتمامات الجديدة بذكاء 🌟
        fields = [
            'username', 'password', 'phone_number', 'user_type', 
            'governorate', 'city', 'address_details', 
            'category', 'interests',  # 🚀 الحقول الجديدة للتخصص والاهتمامات
            'national_id', 'id_front_image', 'id_back_image' # 🔐 الحقول الأمنية والبطاقات الشخصية ثابتة ومحمية
        ]
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'اسم المستخدم'}),
            'phone_number': forms.TextInput(attrs={'placeholder': 'رقم الهاتف'}),
            'address_details': forms.TextInput(attrs={'placeholder': 'اسم الشارع، رقم العقار...'}),
            'national_id': forms.TextInput(attrs={'placeholder': 'الرقم القومي (14 رقم)'}),
            'category': forms.Select(), # قائمة التخصص المهني للفنيين
            'interests': forms.SelectMultiple(attrs={
                'style': 'width: 100%; height: 110px; padding: 8px; border-radius: 8px; background: #f7fafc;',
                'title': 'اضغط مع الاستمرار على زر Ctrl لاختيار أكثر من اهتمام'
            }), # قائمة الاهتمامات المتعددة لطالبي الخدمة
        }


    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

# أضف هذا الكود في نهاية ملف forms.py تماماً
class UserLoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'اسم المستخدم', 'class': 'form-control'}),
        label="اسم المستخدم"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'كلمة المرور', 'class': 'form-control'}),
        label="كلمة المرور"
    )

# أضف هذا الكود في نهاية ملف forms.py تماماً
from .models import Post

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['content', 'image', 'category']
        widgets = {
            'content': forms.Textarea(attrs={'placeholder': 'اكتب تفاصيل طلبك أو اعرض خدماتك هنا...', 'rows': 3, 'style': 'width: 100%; border-radius: 12px; padding: 12px; border: 1px solid #ccc; outline: none; font-family: inherit;'}),
            'category': forms.Select(attrs={'style': 'padding: 10px; border-radius: 20px; border: 1px solid #ccc; outline: none; margin-top: 10px;'}),
        }

# أضف هذا الكود في نهاية ملف forms.py تماماً
from .models import Governorate, City, Category

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
