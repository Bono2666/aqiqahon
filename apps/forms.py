from django import forms
from django.forms import ModelForm
from apps.models import *
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm, UserCreationForm
import datetime
from django.forms import DateInput
from tinymce.widgets import TinyMCE
from django.forms.widgets import TimeInput


def _today_iso():
    return datetime.date.today().isoformat()


class OrderDeliveryDateValidationMixin:
    def _setup_delivery_date_field(self):
        if 'delivery_date' not in self.fields:
            return

        self.fields['delivery_date'].widget.attrs['min'] = _today_iso()
        self.fields['delivery_date'].widget.attrs['type'] = 'date'

    def clean_delivery_date(self):
        delivery_date = self.cleaned_data.get('delivery_date')
        if not delivery_date:
            return delivery_date

        if isinstance(delivery_date, datetime.datetime):
            delivery_day = delivery_date.date()
        else:
            delivery_day = delivery_date

        if delivery_day < datetime.date.today():
            raise forms.ValidationError(
                'Tanggal pengiriman tidak boleh kurang dari hari ini.'
            )

        return delivery_date


class OrderChildBirthValidationMixin:
    def _setup_child_birth_field(self):
        if 'child_birth' not in self.fields:
            return

        self.fields['child_birth'].widget.attrs['max'] = _today_iso()
        self.fields['child_birth'].widget.attrs['type'] = 'date'

    def clean_child_birth(self):
        child_birth = self.cleaned_data.get('child_birth')
        if not child_birth:
            return child_birth

        if isinstance(child_birth, datetime.datetime):
            birth_day = child_birth.date()
        else:
            birth_day = child_birth

        if birth_day > datetime.date.today():
            raise forms.ValidationError(
                'Tanggal lahir tidak boleh melebihi hari ini.'
            )

        return child_birth


class FormUser(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super(FormUser, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['user_id'].label = 'User ID'
        self.fields['username'].label = 'Nama User'
        self.fields['email'].label = 'Email'
        self.fields['position'].label = 'Posisi'
        self.fields['signature'].label = 'Tanda Tangan'
        self.fields['signature'].required = False
        self.fields['password1'].label = 'Password'
        self.fields['password2'].label = 'Konfirmasi Password'
        self.fields['user_id'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['username'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['email'].widget = forms.EmailInput(
            {'class': 'form-control-sm'})
        self.fields['password1'].widget = forms.PasswordInput(
            {'class': 'form-control-sm'})
        self.fields['password2'].widget = forms.PasswordInput(
            {'class': 'form-control-sm'})

    class Meta:
        model = User
        exclude = ['date_joined', 'password', 'is_active', 'is_staff',
                   'is_superuser', 'entry_date', 'entry_by', 'update_date', 'update_by']
        widgets = {
            'signature': forms.FileInput(attrs={'class': 'form-control form-control-sm'}),
        }


class FormUserView(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormUserView, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['username'].label = 'Nama User'
        self.fields['email'].label = 'Email'
        self.fields['position'].label = 'Posisi'
        self.fields['username'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['email'].widget = forms.EmailInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})

    class Meta:
        model = User
        fields = ['user_id', 'username', 'email', 'position', 'signature']

        widgets = {
            'position': forms.Select(attrs={'class': 'form-control form-select-sm', 'disabled': 'disabled'}),
            'signature': forms.FileInput(attrs={'class': 'form-control form-control-sm', 'disabled': 'disabled'}),
        }


class FormUserUpdate(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormUserUpdate, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['username'].label = 'Nama User'
        self.fields['email'].label = 'Email'
        self.fields['position'].label = 'Posisi'
        self.fields['username'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['email'].widget = forms.EmailInput(
            {'class': 'form-control-sm'})
        self.fields['signature'].required = False

    class Meta:
        model = User
        exclude = ['user_id', 'password', 'date_joined',
                   'is_active', 'is_staff', 'is_superuser', 'entry_date', 'entry_by', 'update_date', 'update_by']

        widgets = {
            'position': forms.Select(attrs={'class': 'form-control form-select-sm'}),
            'signature': forms.FileInput(attrs={'class': 'form-control form-control-sm'}),
        }


class FormChangePassword(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super(FormChangePassword, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['old_password'].label = 'Password Lama'
        self.fields['new_password1'].label = 'Password Baru'
        self.fields['new_password2'].label = 'Konfirmasi Password Baru'
        self.fields['old_password'].widget = forms.PasswordInput(
            {'class': 'form-control-sm z-index-2'})
        self.fields['new_password1'].widget = forms.PasswordInput(
            {'class': 'form-control-sm z-index-2'})
        self.fields['new_password2'].widget = forms.PasswordInput(
            {'class': 'form-control-sm z-index-2'})


class FormSetPassword(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super(FormSetPassword, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['new_password1'].label = 'Password Baru'
        self.fields['new_password2'].label = 'Konfirmasi Password Baru'
        self.fields['new_password1'].widget = forms.PasswordInput(
            {'class': 'form-control-sm'})
        self.fields['new_password2'].widget = forms.PasswordInput(
            {'class': 'form-control-sm'})


class FormPromo(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormPromo, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['promo_name'].label = 'Promo Name'
        self.fields['promo_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['promo_limit'].label = 'Limit'
        self.fields['promo_limit'].widget = forms.NumberInput(
            {'class': 'form-control-sm no-spinners'})

    class Meta:
        model = Promo
        exclude = ['entry_date', 'entry_by', 'update_date', 'update_by']


class FormPromoUpdate(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormPromoUpdate, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['promo_name'].label = 'Promo Name'
        self.fields['promo_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['promo_limit'].label = 'Limit'
        self.fields['promo_limit'].widget = forms.NumberInput(
            {'class': 'form-control-sm no-spinners'})

    class Meta:
        model = Promo
        exclude = ['promo_id', 'entry_date',
                   'entry_by', 'update_date', 'update_by']


class FormPromoView(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormPromoView, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['promo_name'].label = 'Promo Name'
        self.fields['promo_name'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['promo_limit'].label = 'Limit'
        self.fields['promo_limit'].widget = forms.NumberInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})

    class Meta:
        model = Promo
        fields = ['promo_id', 'promo_name', 'promo_limit']


class FormAreaSales(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormAreaSales, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['area_id'].label = 'ID Cabang'
        self.fields['area_name'].label = 'Nama Cabang'
        self.fields['manager'].label = 'Manager'
        self.fields['bank_account'].label = 'Bank Account'
        self.fields['address'].label = 'Alamat'
        self.fields['district'].label = 'Kel/Kecamatan'
        self.fields['city'].label = 'Kota/Kabupaten'
        self.fields['postal_code'].label = 'Kode Pos'
        self.fields['address'].required = False
        self.fields['district'].required = False
        self.fields['city'].required = False
        self.fields['postal_code'].required = False
        self.fields['area_id'].widget = forms.TextInput(
            {'class': 'form-control-sm text-uppercase'})
        self.fields['area_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['manager'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['bank_account'].widget = forms.Textarea(
            {'class': 'form-control-sm', 'rows': 7})
        self.fields['address'].widget = forms.Textarea(
            {'class': 'form-control-sm', 'rows': 4})
        self.fields['district'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['city'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['postal_code'].widget = forms.TextInput(
            {'class': 'form-control-sm'})

    class Meta:
        model = AreaSales
        exclude = ['form', 'entry_date',
                   'entry_by', 'update_date', 'update_by']


class FormAreaSalesView(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormAreaSalesView, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['area_name'].label = 'Nama Cabang'
        self.fields['manager'].label = 'Manager'
        self.fields['bank_account'].label = 'Bank Account'
        self.fields['address'].label = 'Alamat'
        self.fields['district'].label = 'Kel/Kecamatan'
        self.fields['city'].label = 'Kota/Kabupaten'
        self.fields['postal_code'].label = 'Kode Pos'
        self.fields['area_name'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['manager'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['bank_account'].widget = forms.Textarea(
            {'class': 'form-control-sm', 'rows': 7, 'readonly': 'readonly'})
        self.fields['address'].widget = forms.Textarea(
            {'class': 'form-control-sm', 'rows': 4, 'readonly': 'readonly'})
        self.fields['district'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['city'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['postal_code'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})

    class Meta:
        model = AreaSales
        fields = ['area_id', 'area_name', 'manager', 'bank_account',
                  'address', 'district', 'city', 'postal_code']


class FormAreaSalesUpdate(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormAreaSalesUpdate, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['area_name'].label = 'Nama Cabang'
        self.fields['manager'].label = 'Manager'
        self.fields['bank_account'].label = 'Bank Account'
        self.fields['address'].label = 'Alamat'
        self.fields['district'].label = 'Kel/Kecamatan'
        self.fields['city'].label = 'Kota/Kabupaten'
        self.fields['postal_code'].label = 'Kode Pos'
        self.fields['address'].required = False
        self.fields['district'].required = False
        self.fields['city'].required = False
        self.fields['postal_code'].required = False
        self.fields['area_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['manager'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['bank_account'].widget = forms.Textarea(
            {'class': 'form-control-sm', 'rows': 7})
        self.fields['address'].widget = forms.Textarea(
            {'class': 'form-control-sm', 'rows': 4})
        self.fields['district'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['city'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['postal_code'].widget = forms.TextInput(
            {'class': 'form-control-sm'})

    class Meta:
        model = AreaSales
        exclude = ['area_id', 'form', 'entry_date',
                   'entry_by', 'update_date', 'update_by']


class FormPosition(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormPosition, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['position_id'].label = 'ID Posisi'
        self.fields['position_name'].label = 'Nama Posisi'
        self.fields['position_id'].widget = forms.TextInput(
            {'class': 'form-control-sm text-uppercase', 'placeholder': 'XXX'})
        self.fields['position_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})

    class Meta:
        model = Position
        exclude = ['entry_date', 'entry_by', 'update_date', 'update_by']


class FormPositionUpdate(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormPositionUpdate, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['position_name'].label = 'Nama Posisi'
        self.fields['position_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})

    class Meta:
        model = Position
        exclude = ['position_id', 'entry_date',
                   'entry_by', 'update_date', 'update_by']


class FormPositionView(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormPositionView, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['position_name'].label = 'Nama Posisi'
        self.fields['position_name'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})

    class Meta:
        model = Position
        fields = ['position_id', 'position_name']


class FormMenu(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormMenu, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['menu_id'].label = 'ID Menu'
        self.fields['menu_name'].label = 'Nama Menu'
        self.fields['menu_remark'].label = 'Deskripsi'
        self.fields['menu_id'].widget = forms.TextInput(
            {'class': 'form-control-sm text-uppercase'})
        self.fields['menu_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['menu_remark'].widget = forms.Textarea(
            {'class': 'form-control-sm', 'rows': 3})

    class Meta:
        model = Menu
        exclude = ['entry_date', 'entry_by', 'update_date', 'update_by']


class FormMenuUpdate(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormMenuUpdate, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['menu_name'].label = 'Nama Menu'
        self.fields['menu_remark'].label = 'Deskripsi'
        self.fields['menu_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['menu_remark'].widget = forms.Textarea(
            {'class': 'form-control-sm', 'rows': 3})

    class Meta:
        model = Menu
        exclude = ['menu_id', 'entry_date',
                   'entry_by', 'update_date', 'update_by']


class FormMenuView(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormMenuView, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['menu_name'].label = 'Nama Menu'
        self.fields['menu_remark'].label = 'Deskripsi'
        self.fields['menu_name'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['menu_remark'].widget = forms.Textarea(
            {'class': 'form-control-sm', 'rows': 3, 'readonly': 'readonly'})

    class Meta:
        model = Menu
        fields = ['menu_id', 'menu_name', 'menu_remark']


class FormAuthUpdate(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormAuthUpdate, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['add'].widget = forms.CheckboxInput(
            {'class': 'border mt-1'})
        self.fields['edit'].widget = forms.CheckboxInput(
            {'class': 'border mt-1'})
        self.fields['delete'].widget = forms.CheckboxInput(
            {'class': 'border mt-1'})

    class Meta:
        model = Auth
        exclude = ['user', 'entry_date',
                   'entry_by', 'update_date', 'update_by']


class FormCuisine(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormCuisine, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['cuisine_id'].label = 'ID Masakan'
        self.fields['cuisine_name'].label = 'Nama Masakan'
        self.fields['cuisine_id'].widget = forms.TextInput(
            {'class': 'form-control-sm text-uppercase'})
        self.fields['cuisine_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})

    class Meta:
        model = Cuisine
        exclude = ['entry_date', 'entry_by', 'update_date', 'update_by']


class FormCuisineUpdate(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormCuisineUpdate, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['cuisine_name'].label = 'Nama Masakan'
        self.fields['cuisine_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})

    class Meta:
        model = Cuisine
        exclude = ['cuisine_id', 'entry_date',
                   'entry_by', 'update_date', 'update_by']


class FormCuisineView(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormCuisineView, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['cuisine_name'].label = 'Nama Masakan'
        self.fields['cuisine_name'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})

    class Meta:
        model = Cuisine
        fields = ['cuisine_id', 'cuisine_name']


class FormEquipment(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormEquipment, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['equipment_id'].label = 'ID Pelengkap'
        self.fields['equipment_name'].label = 'Nama Pelengkap'
        self.fields['tipe'].label = 'Tipe Pelengkap'
        self.fields['equipment_id'].widget = forms.TextInput(
            {'class': 'form-control-sm text-uppercase'})
        self.fields['equipment_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['tipe'].widget.attrs.update(
            {'class': 'form-control form-select-sm'})

    class Meta:
        model = Equipment
        exclude = ['entry_date', 'entry_by', 'update_date', 'update_by']


class FormEquipmentUpdate(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormEquipmentUpdate, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['equipment_name'].label = 'Nama Pelengkap'
        self.fields['tipe'].label = 'Tipe Pelengkap'
        self.fields['equipment_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['tipe'].widget.attrs.update(
            {'class': 'form-control form-select-sm'})

    class Meta:
        model = Equipment
        exclude = ['equipment_id', 'entry_date',
                   'entry_by', 'update_date', 'update_by']


class FormEquipmentView(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormEquipmentView, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['equipment_name'].label = 'Nama Pelengkap'
        self.fields['tipe'].label = 'Tipe Pelengkap'
        self.fields['equipment_name'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['tipe'].widget.attrs.update(
            {'class': 'form-control form-select-sm', 'disabled': 'disabled'})

    class Meta:
        model = Equipment
        fields = ['equipment_id', 'equipment_name', 'tipe']


class FormCategory(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormCategory, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['category_id'].label = 'ID Kategori'
        self.fields['category_name'].label = 'Nama Kategori'
        self.fields['category_id'].widget = forms.TextInput(
            {'class': 'form-control-sm text-uppercase'})
        self.fields['category_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})

    class Meta:
        model = Category
        fields = ['category_id', 'category_name']


class FormCategoryUpdate(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormCategoryUpdate, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['category_name'].label = 'Nama Kategori'
        self.fields['category_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})

    class Meta:
        model = Category
        fields = ['category_name']


class FormCategoryView(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormCategoryView, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['category_name'].label = 'Nama Kategori'
        self.fields['category_name'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})

    class Meta:
        model = Category
        fields = ['category_id', 'category_name']


class FormGoatType(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormGoatType, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['goat_type_id'].label = 'Kode Jenis'
        self.fields['goat_type_name'].label = 'Nama Jenis'
        self.fields['display_order'].label = 'Urutan'
        self.fields['goat_type_id'].widget = forms.TextInput(
            {'class': 'form-control-sm text-uppercase'})
        self.fields['goat_type_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['display_order'].widget = forms.NumberInput(
            {'class': 'form-control-sm no-spinners'})

    class Meta:
        model = GoatType
        fields = ['goat_type_id', 'goat_type_name', 'display_order']


class FormGoatTypeUpdate(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormGoatTypeUpdate, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['goat_type_name'].label = 'Nama Jenis'
        self.fields['display_order'].label = 'Urutan'
        self.fields['goat_type_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['display_order'].widget = forms.NumberInput(
            {'class': 'form-control-sm no-spinners'})

    class Meta:
        model = GoatType
        fields = ['goat_type_name', 'display_order']


class FormGoatTypeView(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormGoatTypeView, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['goat_type_name'].label = 'Nama Jenis'
        self.fields['display_order'].label = 'Urutan'
        self.fields['goat_type_name'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['display_order'].widget = forms.NumberInput(
            {'class': 'form-control-sm no-spinners', 'readonly': 'readonly'})

    class Meta:
        model = GoatType
        fields = ['goat_type_id', 'goat_type_name', 'display_order']


class FormDashboard(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormDashboard, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['dashboard_id'].label = 'Kode Dashboard'
        self.fields['dashboard_name'].label = 'Nama Dashboard'
        self.fields['display_order'].label = 'Urutan'
        self.fields['dashboard_id'].widget = forms.TextInput(
            {'class': 'form-control-sm text-uppercase'})
        self.fields['dashboard_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['display_order'].widget = forms.NumberInput(
            {'class': 'form-control-sm no-spinners'})

    class Meta:
        model = Dashboard
        fields = ['dashboard_id', 'dashboard_name', 'display_order']


class FormDashboardUpdate(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormDashboardUpdate, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['dashboard_name'].label = 'Nama Dashboard'
        self.fields['display_order'].label = 'Urutan'
        self.fields['dashboard_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['display_order'].widget = forms.NumberInput(
            {'class': 'form-control-sm no-spinners'})

    class Meta:
        model = Dashboard
        fields = ['dashboard_name', 'display_order']


class FormDashboardView(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormDashboardView, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['dashboard_name'].label = 'Nama Dashboard'
        self.fields['display_order'].label = 'Urutan'
        self.fields['dashboard_name'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['display_order'].widget = forms.NumberInput(
            {'class': 'form-control-sm no-spinners', 'readonly': 'readonly'})

    class Meta:
        model = Dashboard
        fields = ['dashboard_id', 'dashboard_name', 'display_order']


class FormPackage(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormPackage, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['package_id'].label = 'ID Paket'
        self.fields['package_name'].label = 'Nama Paket'
        self.fields['category'].label = 'Kategori'
        self.fields['male_price'].label = 'Harga Jual Jantan'
        self.fields['female_price'].label = 'Harga Jual Betina'
        self.fields['box'].label = 'Jumlah Box'
        self.fields['quantity'].label = 'Jumlah Kambing'
        self.fields['type'].label = 'Tipe Kambing'
        self.fields['goat_type'].label = 'Jenis Kambing 1'
        self.fields['goat_type2'].label = 'Jenis Kambing 2'
        self.fields['dashboard'].label = 'Dashboard'
        self.fields['package_id'].widget = forms.TextInput(
            {'class': 'form-control-sm text-uppercase'})
        self.fields['package_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['male_price'].widget = forms.NumberInput(
            {'class': 'form-control-sm no-spinners'})
        self.fields['female_price'].widget = forms.NumberInput(
            {'class': 'form-control-sm no-spinners'})
        self.fields['box'].widget = forms.NumberInput(
            {'class': 'form-control-sm no-spinners'})
        self.fields['quantity'].widget = forms.NumberInput(
            {'class': 'form-control-sm no-spinners'})

    class Meta:
        model = Package
        exclude = ['entry_date', 'entry_by', 'update_date', 'update_by']


class FormPackageUpdate(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormPackageUpdate, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['package_name'].label = 'Nama Paket'
        self.fields['category'].label = 'Kategori'
        self.fields['male_price'].label = 'Harga Jual Jantan'
        self.fields['female_price'].label = 'Harga Jual Betina'
        self.fields['box'].label = 'Jumlah Box'
        self.fields['quantity'].label = 'Jumlah Kambing'
        self.fields['type'].label = 'Tipe Kambing'
        self.fields['goat_type'].label = 'Jenis Kambing 1'
        self.fields['goat_type2'].label = 'Jenis Kambing 2'
        self.fields['dashboard'].label = 'Dashboard'
        self.fields['package_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['male_price'].widget = forms.NumberInput(
            {'class': 'form-control-sm no-spinners'})
        self.fields['female_price'].widget = forms.NumberInput(
            {'class': 'form-control-sm no-spinners'})
        self.fields['box'].widget = forms.NumberInput(
            {'class': 'form-control-sm no-spinners'})
        self.fields['quantity'].widget = forms.NumberInput(
            {'class': 'form-control-sm no-spinners'})

    class Meta:
        model = Package
        exclude = ['package_id', 'entry_date',
                   'entry_by', 'update_date', 'update_by']


class FormPackageView(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormPackageView, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['package_name'].label = 'Nama Paket'
        self.fields['category'].label = 'Kategori'
        self.fields['male_price'].label = 'Harga Jual Jantan'
        self.fields['female_price'].label = 'Harga Jual Betina'
        self.fields['box'].label = 'Jumlah Box'
        self.fields['quantity'].label = 'Jumlah Kambing'
        self.fields['type'].label = 'Tipe Kambing'
        self.fields['goat_type'].label = 'Jenis Kambing 1'
        self.fields['goat_type2'].label = 'Jenis Kambing 2'
        self.fields['dashboard'].label = 'Dashboard'
        self.fields['package_name'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['male_price'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['female_price'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['box'].widget = forms.NumberInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['quantity'].widget = forms.NumberInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})

    class Meta:
        model = Package
        fields = ['package_id', 'package_name', 'category',
                  'male_price', 'female_price', 'box', 'quantity', 'type', 'goat_type', 'goat_type2', 'dashboard']


class DateInput(forms.DateInput):
    input_type = 'date'


class FormRegion(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormRegion, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['region_id'].label = 'Region ID'
        self.fields['region_id'].widget = forms.TextInput(
            {'class': 'form-control-sm text-uppercase'})
        self.fields['region_name'].label = 'Region Name'
        self.fields['region_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})

    class Meta:
        model = Region
        fields = ['region_id', 'region_name']


class FormRegionUpdate(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormRegionUpdate, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['region_name'].label = 'Region Name'
        self.fields['region_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})

    class Meta:
        model = Region
        fields = ['region_name']


class FormRegionView(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormRegionView, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['region_name'].label = 'Region Name'
        self.fields['region_name'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})

    class Meta:
        model = Region
        fields = ['region_id', 'region_name']


class FormCustomer(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormCustomer, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['customer_name'].label = 'Nama Customer'
        self.fields['customer_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['customer_address'].label = 'Alamat'
        self.fields['customer_address'].widget = forms.Textarea(
            {'class': 'form-control-sm', 'rows': 4})
        self.fields['customer_district'].label = 'Kecamatan'
        self.fields['customer_district'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['customer_city'].label = 'Kota'
        self.fields['customer_city'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['customer_province'].label = 'Propinsi'
        self.fields['customer_province'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['customer_phone'].label = 'Telepon 1'
        self.fields['customer_phone'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['customer_phone2'].label = 'Telepon 2'
        self.fields['customer_phone2'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['customer_email'].label = 'Email'
        self.fields['customer_email'].widget = forms.EmailInput(
            {'class': 'form-control-sm'})

    class Meta:
        model = Customer
        exclude = ['entry_date', 'entry_by', 'update_date', 'update_by']


class FormCustomerUpdate(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormCustomerUpdate, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['customer_name'].label = 'Nama Customer'
        self.fields['customer_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['customer_address'].label = 'Alamat'
        self.fields['customer_address'].widget = forms.Textarea(
            {'class': 'form-control-sm', 'rows': 4})
        self.fields['customer_district'].label = 'Kecamatan'
        self.fields['customer_district'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['customer_city'].label = 'Kota'
        self.fields['customer_city'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['customer_province'].label = 'Propinsi'
        self.fields['customer_province'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['customer_phone'].label = 'Telepon 1'
        self.fields['customer_phone'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['customer_phone2'].label = 'Telepon 2'
        self.fields['customer_phone2'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['customer_email'].label = 'Email'
        self.fields['customer_email'].widget = forms.EmailInput(
            {'class': 'form-control-sm'})

    class Meta:
        model = Customer
        exclude = ['entry_date', 'entry_by', 'update_date', 'update_by']


class FormCustomerView(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormCustomerView, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['customer_name'].label = 'Nama Customer'
        self.fields['customer_name'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['customer_address'].label = 'Alamat'
        self.fields['customer_address'].widget = forms.Textarea(
            {'class': 'form-control-sm', 'rows': 4, 'readonly': 'readonly'})
        self.fields['customer_district'].label = 'Kecamatan'
        self.fields['customer_district'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['customer_city'].label = 'Kota'
        self.fields['customer_city'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['customer_province'].label = 'Propinsi'
        self.fields['customer_province'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['customer_phone'].label = 'Telepon 1'
        self.fields['customer_phone'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['customer_phone2'].label = 'Telepon 2'
        self.fields['customer_phone2'].widget = forms.TextInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['customer_email'].label = 'Email'
        self.fields['customer_email'].widget = forms.EmailInput(
            {'class': 'form-control-sm', 'readonly': 'readonly'})

    class Meta:
        model = Customer
        fields = ['customer_id', 'customer_name', 'customer_address',
                  'customer_district', 'customer_city', 'customer_province', 'customer_phone', 'customer_phone2', 'customer_email']


class FormCustomerDetail(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormCustomerDetail, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['child_name'].label = 'Nama Anak'
        self.fields['child_name'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['child_birth'].label = 'Tanggal Lahir'
        self.fields['child_sex'].label = 'Jenis Kelamin'
        self.fields['child_sex'].widget = forms.Select(
            attrs={'class': 'form-control-sm'})
        self.fields['child_father'].label = 'Nama Ayah'
        self.fields['child_father'].widget = forms.TextInput(
            {'class': 'form-control-sm'})
        self.fields['child_mother'].label = 'Nama Ibu'
        self.fields['child_mother'].widget = forms.TextInput(
            {'class': 'form-control-sm'})

    class Meta:
        model = CustomerDetail
        exclude = ['customer', 'entry_date', 'entry_by',
                   'update_date', 'update_by']

        widgets = {
            'child_birth': DateInput(attrs={'class': 'form-control form-control-sm', 'data-provide': 'datepicker', 'data-date-format': 'dd/mm/yyyy', 'default': datetime.date.today().strftime('%d/%m/%Y')}),
        }


class FormOrder(OrderDeliveryDateValidationMixin, ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormOrder, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['order_id'].widget = forms.TextInput(
            attrs={'class': 'd-none'})
        self.fields['order_date'].widget = forms.DateInput(
            attrs={'class': 'form-control-sm d-none', 'readonly': 'readonly'})
        self.fields['order_date'].input_formats = ['%d/%m/%Y']
        self.fields['order_date'].initial = datetime.date.today().strftime(
            '%d/%m/%Y')
        self.fields['customer_name'].label = 'Nama Lengkap Pemesan'
        self.fields['customer_name'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm'})
        self.fields['customer_phone'].label = 'Telepon 1'
        self.fields['customer_phone'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm', 'placeholder': '08xxxxxxxxxx'})
        self.fields['customer_phone2'].label = 'Telepon 2'
        self.fields['customer_phone2'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm', 'placeholder': '08xxxxxxxxxx'})
        self.fields['customer_email'].label = 'Email'
        self.fields['customer_email'].widget = forms.EmailInput(
            attrs={'class': 'form-control-sm'})
        self.fields['customer_email'].required = False
        self.fields['customer_address'].label = 'Alamat Lengkap Pengiriman'
        self.fields['customer_district'].label = 'Kecamatan'
        self.fields['customer_district'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm'})
        self.fields['customer_city'].label = 'Kota/Kabupaten'
        self.fields['customer_city'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm'})
        self.fields['customer_province'].label = 'Propinsi'
        self.fields['customer_province'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm'})
        self.fields['delivery_date'].label = 'Tanggal Pengiriman'
        self.fields['time_arrival'].label = 'Jam Acara'
        self._setup_delivery_date_field()

    class Meta:
        model = Order
        fields = ['order_id', 'order_date', 'customer_name', 'customer_phone', 'customer_phone2', 'customer_email', 'customer_address',
                  'customer_district', 'customer_city', 'customer_province', 'delivery_date', 'time_arrival']

        widgets = {
            'customer_address': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 4}),
            'delivery_date': DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'time_arrival': TimeInput(attrs={'class': 'form-control form-control-sm', 'data-provide': 'timepicker', 'data-time-format': 'HH:ii', 'type': 'time'}),
        }


class FormOrderUpdate(OrderDeliveryDateValidationMixin, ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormOrderUpdate, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['customer_name'].label = 'Nama Lengkap Pemesan'
        self.fields['customer_name'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm'})
        self.fields['customer_phone'].label = 'Telepon 1'
        self.fields['customer_phone'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm', 'placeholder': '08xxxxxxxxxx'})
        self.fields['customer_phone2'].label = 'Telepon 2'
        self.fields['customer_phone2'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm', 'placeholder': '08xxxxxxxxxx'})
        self.fields['customer_email'].label = 'Email'
        self.fields['customer_email'].widget = forms.EmailInput(
            attrs={'class': 'form-control-sm'})
        self.fields['customer_email'].required = False
        self.fields['customer_address'].label = 'Alamat Lengkap Pengiriman'
        self.fields['customer_district'].label = 'Kecamatan'
        self.fields['customer_district'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm'})
        self.fields['customer_city'].label = 'Kota/Kabupaten'
        self.fields['customer_city'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm'})
        self.fields['customer_province'].label = 'Propinsi'
        self.fields['customer_province'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm'})
        self.fields['delivery_date'].label = 'Tanggal Pengiriman'
        self.fields['time_arrival'].label = 'Jam Acara'
        self._setup_delivery_date_field()

    class Meta:
        model = Order
        fields = ['customer_name', 'customer_phone', 'customer_phone2', 'customer_email', 'customer_address',
                  'customer_district', 'customer_city', 'customer_province', 'delivery_date', 'time_arrival']

        widgets = {
            'customer_address': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 4}),
            'delivery_date': DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'time_arrival': TimeInput(attrs={'class': 'form-control form-control-sm', 'data-provide': 'timepicker', 'data-time-format': 'HH:ii', 'type': 'time'}),
        }


class FormOrderChild(OrderChildBirthValidationMixin, ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormOrderChild, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['order'].widget = forms.TextInput(
            attrs={'class': 'd-none'})
        self.fields['child_name'].label = 'Nama Anak Yang Diaqiqahkan'
        self.fields['child_name'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm'})
        self.fields['child_birth'].label = 'Tanggal Lahir'
        self.fields['child_sex'].label = 'Jenis Kelamin'
        self.fields['child_father'].label = 'Nama Ayah'
        self.fields['child_father'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm'})
        self.fields['child_mother'].label = 'Nama Ibu'
        self.fields['child_mother'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm'})
        self._setup_child_birth_field()

    class Meta:
        model = OrderChild
        exclude = ['entry_date', 'entry_by', 'update_date', 'update_by']

        widgets = {
            'child_birth': DateInput(attrs={'class': 'form-control form-control-sm', 'data-provide': 'datepicker', 'data-date-format': 'dd/mm/yyyy'}),
        }


class FormOrderCSChild(OrderChildBirthValidationMixin, ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormOrderCSChild, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['child_name'].label = 'Nama Anak Yang Diaqiqahkan'
        self.fields['child_name'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm'})
        self.fields['child_birth'].label = 'Tanggal Lahir'
        self.fields['child_sex'].label = 'Jenis Kelamin'
        self.fields['child_father'].label = 'Nama Ayah'
        self.fields['child_father'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm'})
        self.fields['child_mother'].label = 'Nama Ibu'
        self.fields['child_mother'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm'})
        self._setup_child_birth_field()

    class Meta:
        model = OrderChild
        exclude = ['order', 'entry_date',
                   'entry_by', 'update_date', 'update_by']

        widgets = {
            'child_birth': DateInput(attrs={'class': 'form-control form-control-sm', 'data-provide': 'datepicker', 'data-date-format': 'dd/mm/yyyy'}),
        }


class FormOrderChildUpdate(OrderChildBirthValidationMixin, ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormOrderChildUpdate, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['child_name'].label = 'Nama Anak Yang Diaqiqahkan'
        self.fields['child_name'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm'})
        self.fields['child_birth'].label = 'Tanggal Lahir'
        self.fields['child_sex'].label = 'Jenis Kelamin'
        self.fields['child_father'].label = 'Nama Ayah'
        self.fields['child_father'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm'})
        self.fields['child_mother'].label = 'Nama Ibu'
        self.fields['child_mother'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm'})
        self._setup_child_birth_field()

    class Meta:
        model = OrderChild
        exclude = ['order', 'entry_date',
                   'entry_by', 'update_date', 'update_by']

        widgets = {
            'child_birth': DateInput(attrs={'class': 'form-control form-control-sm', 'data-provide': 'datepicker', 'data-date-format': 'dd/mm/yyyy'}),
        }


class FormOrderPackage(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormOrderPackage, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['quantity'].label = 'Jumlah Paket'

    class Meta:
        model = OrderPackage
        exclude = ['order', 'total_price', 'category', 'package', 'type', 'entry_date', 'main_cuisine', 'main_cuisine_price', 'sub_cuisine', 'side_cuisine1', 'side_cuisine2', 'side_cuisine3', 'side_cuisine4', 'side_cuisine5', 'unit_price', 'extra_price', 'rice', 'bag', 'box_qty', 'box_type', 'upgrade', 'beverage', 'souvenir',
                   'entry_by', 'update_date', 'update_by']

        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 1, 'value': 1}),
        }


class FormOrderConfirmUpdate(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormOrderConfirmUpdate, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['order_note'].label = 'Catatan Pemesanan (Jika Ada)'
        self.fields['order_note'].required = False

    class Meta:
        model = Order
        fields = ['order_note']

        widgets = {
            'order_note': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }


class FormOrderView(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormOrderView, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['order_date'].widget = forms.DateInput(
            attrs={'class': 'form-control-sm d-none', 'readonly': 'readonly'})
        self.fields['customer_name'].label = 'Nama Lengkap Pemesan'
        self.fields['customer_name'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['customer_phone'].label = 'Telepon'
        self.fields['customer_phone'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['customer_email'].label = 'Email'
        self.fields['customer_email'].widget = forms.EmailInput(
            attrs={'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['customer_address'].label = 'Alamat Lengkap Pengiriman'
        self.fields['customer_district'].label = 'Kecamatan'
        self.fields['customer_district'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['customer_city'].label = 'Kota/Kabupaten'
        self.fields['customer_city'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['customer_province'].label = 'Propinsi'
        self.fields['customer_province'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['delivery_date'].label = 'Tanggal Pengiriman'
        self.fields['time_arrival'].label = 'Jam Acara'
        self.fields['order_note'].label = 'Catatan Pemesanan (Jika Ada)'
        self.fields['order_note'].required = False

    class Meta:
        model = Order
        fields = ['order_date', 'customer_name', 'customer_phone', 'customer_email', 'customer_address',
                  'customer_district', 'customer_city', 'customer_province', 'delivery_date', 'time_arrival', 'order_note']

        widgets = {
            'customer_address': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 4, 'readonly': 'readonly'}),
            'delivery_date': DateInput(attrs={'class': 'form-control form-control-sm', 'disabled': 'disabled'}),
            'time_arrival': TimeInput(attrs={'class': 'form-control form-control-sm', 'data-provide': 'timepicker', 'data-time-format': 'HH:ii', 'type': 'time', 'disabled': 'disabled'}),
            'order_note': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3, 'readonly': 'readonly'}),
        }


class FormOrderCSUpdate(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormOrderCSUpdate, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        # self.fields['order_date'].widget = forms.DateInput(
        #     attrs={'class': 'form-control-sm d-none', 'readonly': 'readonly'})
        # self.fields['customer_name'].label = 'Nama Lengkap Pemesan'
        # self.fields['customer_name'].widget = forms.TextInput(
        #     attrs={'class': 'form-control-sm'})
        # self.fields['customer_phone'].label = 'Telepon'
        # self.fields['customer_phone'].widget = forms.TextInput(
        #     attrs={'class': 'form-control-sm'})
        # self.fields['customer_email'].label = 'Email'
        # self.fields['customer_email'].widget = forms.EmailInput(
        #     attrs={'class': 'form-control-sm'})
        # self.fields['customer_address'].label = 'Alamat Lengkap Pengiriman'
        # self.fields['customer_district'].label = 'Kecamatan'
        # self.fields['customer_district'].widget = forms.TextInput(
        #     attrs={'class': 'form-control-sm'})
        # self.fields['customer_city'].label = 'Kota/Kabupaten'
        # self.fields['customer_city'].widget = forms.TextInput(
        #     attrs={'class': 'form-control-sm'})
        # self.fields['customer_province'].label = 'Propinsi'
        # self.fields['customer_province'].widget = forms.TextInput(
        #     attrs={'class': 'form-control-sm'})
        # self.fields['delivery_date'].label = 'Tanggal Pengiriman'
        # self.fields['time_arrival'].label = 'Jam Acara'
        # self.fields['order_note'].label = 'Catatan Pemesanan (Jika Ada)'
        # self.fields['order_note'].required = False

    class Meta:
        model = Order
        fields = []

        widgets = {
            # 'customer_address': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 4}),
            # 'delivery_date': DateInput(attrs={'class': 'form-control form-control-sm', 'data-provide': 'datepicker', 'data-date-format': 'dd/mm/yyyy'}),
            # 'time_arrival': TimeInput(attrs={'class': 'form-control form-control-sm', 'data-provide': 'timepicker', 'data-time-format': 'HH:ii', 'type': 'time'}),
            # 'order_note': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }


class FormCashIn(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormCashIn, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['cashin_type'].label = 'Cara Pembayaran'
        self.fields['cashin_date'].label = 'Tanggal Pembayaran'
        self.fields['cashin_amount'].label = 'Jumlah Uang Masuk'
        self.fields['cashin_amount'].widget = forms.NumberInput(
            attrs={'class': 'form-control-sm no-spinners', 'min': 1})
        self.fields['bank'].label = 'Nama Bank'
        self.fields['bank'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm'})
        self.fields['bank'].required = False
        self.fields['evidence'].label = 'Bukti Pembayaran'
        self.fields['cashin_note'].label = 'Catatan'
        self.fields['cashin_note'].required = False

    class Meta:
        model = CashIn
        exclude = ['order', 'entry_date',
                   'entry_by', 'update_date', 'update_by']

        widgets = {
            'cashin_date': DateInput(attrs={'class': 'form-control form-control-sm', 'data-provide': 'datepicker', 'data-date-format': 'dd/mm/yyyy'}),
            'evidence': forms.FileInput(attrs={'class': 'form-control form-control-sm'}),
            'cashin_note': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }


class FormCashInView(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormCashInView, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['cashin_type'].label = 'Cara Pembayaran'
        self.fields['cashin_date'].label = 'Tanggal Pembayaran'
        self.fields['cashin_amount'].label = 'Jumlah Uang Masuk'
        self.fields['cashin_amount'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['bank'].label = 'Nama Bank'
        self.fields['bank'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm', 'readonly': 'readonly'})
        self.fields['evidence'].label = 'Bukti Pembayaran'
        self.fields['cashin_note'].label = 'Catatan'
        self.fields['cashin_note'].widget = forms.Textarea(
            attrs={'class': 'form-control-sm', 'rows': 3, 'readonly': 'readonly'})

    class Meta:
        model = CashIn
        exclude = ['order', 'cashin_id', 'entry_date',
                   'entry_by', 'update_date', 'update_by']

        widgets = {
            'cashin_date': DateInput(attrs={'class': 'form-control form-control-sm', 'readonly': 'readonly'}),
            'evidence': forms.FileInput(attrs={'class': 'form-control form-control-sm', 'disabled': 'disabled'}),
        }


class FormCashInUpdate(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormCashInUpdate, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.fields['cashin_type'].label = 'Cara Pembayaran'
        self.fields['cashin_date'].label = 'Tanggal Pembayaran'
        self.fields['cashin_amount'].label = 'Jumlah Uang Masuk'
        self.fields['cashin_amount'].widget = forms.NumberInput(
            attrs={'class': 'form-control-sm no-spinners', 'min': 1})
        self.fields['bank'].label = 'Nama Bank'
        self.fields['bank'].widget = forms.TextInput(
            attrs={'class': 'form-control-sm'})
        self.fields['bank'].required = False
        self.fields['evidence'].label = 'Bukti Pembayaran'
        self.fields['cashin_note'].label = 'Catatan'
        self.fields['cashin_note'].required = False

    class Meta:
        model = CashIn
        exclude = ['order', 'entry_date', 'entry_by',
                   'update_date', 'update_by', 'order']

        widgets = {
            'cashin_date': DateInput(attrs={'class': 'form-control form-control-sm', 'data-provide': 'datepicker', 'data-date-format': 'dd/mm/yyyy'}),
            'evidence': forms.FileInput(attrs={'class': 'form-control form-control-sm'}),
            'cashin_note': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }
