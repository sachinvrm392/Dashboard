import string
import secrets
from django import forms
from django.contrib.auth import get_user_model
from accounts.models import BusinessPartner

User = get_user_model()

class BPCreateForm(forms.ModelForm):
    username = forms.CharField(
        max_length=150, 
        required=True,
        error_messages={'required': 'Username is required.'},
        widget=forms.TextInput(attrs={'placeholder': 'e.g. acme_partner'})
    )
    temp_password = forms.CharField(
        max_length=128, 
        required=True, 
        error_messages={'required': 'Temporary password is required.'},
        widget=forms.PasswordInput(attrs={'placeholder': 'Assign temporary password'})
    )

    class Meta:
        model = BusinessPartner
        fields = [
            'company_name', 'contact_person', 'email', 'phone', 
            'address', 'logo', 'elevenlabs_api_key', 'credit_alert_threshold'
        ]
        error_messages = {
            'company_name': {'required': 'Company name is required.'},
            'contact_person': {'required': 'Contact person is required.'},
            'email': {'required': 'Email address is required.'},
            'credit_alert_threshold': {'required': 'Credit limit is required.'},
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and not self.initial.get('credit_alert_threshold'):
            self.initial['credit_alert_threshold'] = 1000
        # Generate random secure password suggestion
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        suggested_password = ''.join(secrets.choice(alphabet) for i in range(12))
        self.fields['temp_password'].help_text = f"Suggested secure password: {suggested_password}"
        
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            
    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise forms.ValidationError("Username is required.")
        if len(username) < 3:
            raise forms.ValidationError("Username must be at least 3 characters long.")
        if ' ' in username:
            raise forms.ValidationError("Username cannot contain spaces.")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def clean_temp_password(self):
        password = self.cleaned_data.get('temp_password', '')
        if len(password) < 8:
            raise forms.ValidationError("Temporary password must be at least 8 characters long.")
        return password

    def clean_company_name(self):
        name = self.cleaned_data.get('company_name', '').strip()
        if not name:
            raise forms.ValidationError("Company name is required.")
        if len(name) < 2:
            raise forms.ValidationError("Company name must be at least 2 characters.")
        if BusinessPartner.objects.filter(company_name__iexact=name).exists():
            raise forms.ValidationError("A business partner with this company name already exists.")
        return name

    def clean_contact_person(self):
        person = self.cleaned_data.get('contact_person', '').strip()
        if not person:
            raise forms.ValidationError("Contact person is required.")
        if len(person) < 2:
            raise forms.ValidationError("Contact person name must be at least 2 characters.")
        return person

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise forms.ValidationError("Email address is required.")
        if BusinessPartner.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A business partner with this email is already registered.")
        return email

    def clean_credit_alert_threshold(self):
        threshold = self.cleaned_data.get('credit_alert_threshold')
        if threshold is None or threshold < 1:
            raise forms.ValidationError("Credit limit must be at least 1 credit.")
        return threshold

    def clean_elevenlabs_api_key(self):
        return self.cleaned_data.get('elevenlabs_api_key', '').strip()

    def save(self, commit=True):
        username = self.cleaned_data['username']
        temp_password = self.cleaned_data['temp_password']
        email = self.cleaned_data.get('email', '')
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=temp_password,
            role=User.Role.BUSINESS_PARTNER,
            must_change_password=True
        )
        
        bp = super().save(commit=False)
        bp.user = user
        if commit:
            bp.save()
        return bp


class BPUpdateForm(forms.ModelForm):
    class Meta:
        model = BusinessPartner
        fields = [
            'company_name', 'contact_person', 'email', 'phone', 
            'address', 'logo', 'elevenlabs_api_key', 'credit_alert_threshold'
        ]
        error_messages = {
            'company_name': {'required': 'Company name is required.'},
            'contact_person': {'required': 'Contact person is required.'},
            'email': {'required': 'Email address is required.'},
            'credit_alert_threshold': {'required': 'Credit limit is required.'},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

    def clean_company_name(self):
        name = self.cleaned_data.get('company_name', '').strip()
        if not name:
            raise forms.ValidationError("Company name is required.")
        if len(name) < 2:
            raise forms.ValidationError("Company name must be at least 2 characters.")
        existing = BusinessPartner.objects.filter(company_name__iexact=name)
        if self.instance and self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError("A business partner with this company name already exists.")
        return name

    def clean_contact_person(self):
        person = self.cleaned_data.get('contact_person', '').strip()
        if not person:
            raise forms.ValidationError("Contact person is required.")
        if len(person) < 2:
            raise forms.ValidationError("Contact person name must be at least 2 characters.")
        return person

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise forms.ValidationError("Email address is required.")
        existing = BusinessPartner.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError("A business partner with this email is already registered.")
        return email

    def clean_credit_alert_threshold(self):
        threshold = self.cleaned_data.get('credit_alert_threshold')
        if threshold is None or threshold < 1:
            raise forms.ValidationError("Credit limit must be at least 1 credit.")
        return threshold

    def clean_elevenlabs_api_key(self):
        return self.cleaned_data.get('elevenlabs_api_key', '').strip()


class UserProfileForm(forms.Form):
    first_name = forms.CharField(
        max_length=150, 
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter first name'})
    )
    last_name = forms.CharField(
        max_length=150, 
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter last name'})
    )
    email = forms.EmailField(
        required=True,
        error_messages={'required': 'Email address is required.'},
        widget=forms.EmailInput(attrs={'placeholder': 'name@example.com'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '+1 (555) 000-0000'})
    )
    company_name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Company name'})
    )
    contact_person = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Contact person name'})
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Office or billing address'})
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['first_name'].initial = user.first_name
        self.fields['last_name'].initial = user.last_name
        self.fields['email'].initial = user.email

        if hasattr(user, 'business_partner'):
            bp = user.business_partner
            self.fields['phone'].initial = bp.phone
            self.fields['company_name'].initial = bp.company_name
            self.fields['contact_person'].initial = bp.contact_person
            self.fields['address'].initial = bp.address

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise forms.ValidationError("Email is required.")
        # If the user is changing their email to a new one, verify it's not taken by another user
        if email != (self.user.email or '').strip().lower():
            if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
                raise forms.ValidationError("This email is already associated with another user account.")
        return email

    def save(self):
        self.user.first_name = self.cleaned_data.get('first_name', '').strip()
        self.user.last_name = self.cleaned_data.get('last_name', '').strip()
        self.user.email = self.cleaned_data.get('email', '').strip().lower()
        self.user.save()

        if hasattr(self.user, 'business_partner'):
            bp = self.user.business_partner
            if 'phone' in self.cleaned_data:
                bp.phone = self.cleaned_data['phone'].strip()
            if 'company_name' in self.cleaned_data and self.cleaned_data['company_name']:
                bp.company_name = self.cleaned_data['company_name'].strip()
            if 'contact_person' in self.cleaned_data and self.cleaned_data['contact_person']:
                bp.contact_person = self.cleaned_data['contact_person'].strip()
            if 'address' in self.cleaned_data:
                bp.address = self.cleaned_data['address'].strip()
            bp.email = self.user.email
            bp.save()
        return self.user

