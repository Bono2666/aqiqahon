from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from crum import get_current_user
from decimal import Decimal
from re import sub
from django.db import models
from tinymce.models import HTMLField


class User(AbstractUser):
    is_active = models.BooleanField(default=True)
    user_id = models.CharField(max_length=50, primary_key=True)
    username = models.CharField(max_length=50)
    position = models.ForeignKey(
        'Position', on_delete=models.CASCADE, null=True)
    signature = models.ImageField(upload_to='signature/', null=True)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True)
    update_by = models.CharField(max_length=50, null=True)

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(User, self).save(*args, **kwargs)

    USERNAME_FIELD = 'user_id'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.username


class Cuisine(models.Model):
    cuisine_id = models.CharField(max_length=50, primary_key=True)
    cuisine_name = models.CharField(max_length=50)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True)
    update_by = models.CharField(max_length=50, null=True)

    def save(self, *args, **kwargs):
        self.cuisine_id = self.cuisine_id.upper()
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(Cuisine, self).save(*args, **kwargs)

    def __str__(self):
        return self.cuisine_name


class Equipment(models.Model):
    TIPE_EQUIPMENT_CHOICES = [
        ('', '-- Pilih Tipe --'),
        ('Kemasan Dan Souvenir', 'Kemasan Dan Souvenir'),
        ('Masakan', 'Masakan'),
        ('Olahan Dan Pendamping', 'Olahan Dan Pendamping'),
        ('Box Paket', 'Box Paket'),
    ]

    equipment_id = models.CharField(max_length=50, primary_key=True)
    equipment_name = models.CharField(max_length=50)
    tipe = models.CharField(max_length=50, choices=TIPE_EQUIPMENT_CHOICES, blank=True, null=True)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True)
    update_by = models.CharField(max_length=50, null=True)

    def save(self, *args, **kwargs):
        self.equipment_id = self.equipment_id.upper()
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(Equipment, self).save(*args, **kwargs)

    def __str__(self):
        return self.equipment_name


class Category(models.Model):
    category_id = models.CharField(max_length=50, primary_key=True)
    category_name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True)
    update_by = models.CharField(max_length=50, null=True)

    def save(self, *args, **kwargs):
        self.category_id = self.category_id.upper()
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(Category, self).save(*args, **kwargs)

    def __str__(self):
        return self.category_name


class GoatType(models.Model):
    goat_type_id = models.CharField(max_length=20, primary_key=True)
    goat_type_name = models.CharField(max_length=50)
    display_order = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True, blank=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.goat_type_id = self.goat_type_id.upper()
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(GoatType, self).save(*args, **kwargs)

    def __str__(self):
        return self.goat_type_name


class Dashboard(models.Model):
    dashboard_id = models.CharField(max_length=20, primary_key=True)
    dashboard_name = models.CharField(max_length=50)
    display_order = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True, blank=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.dashboard_id = self.dashboard_id.upper()
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(Dashboard, self).save(*args, **kwargs)

    def __str__(self):
        return self.dashboard_name


class Package(models.Model):
    package_id = models.CharField(max_length=50, primary_key=True)
    package_name = models.CharField(max_length=50)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    promo = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    male_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    female_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    box = models.IntegerField(default=0)
    quantity = models.IntegerField(default=0)
    type = models.CharField(max_length=10, null=True)
    goat_type = models.ForeignKey(GoatType, on_delete=models.CASCADE, null=True, blank=True)
    dashboard = models.ForeignKey(Dashboard, on_delete=models.SET_NULL, null=True, blank=True)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True, blank=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.package_id = self.package_id.upper()
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(Package, self).save(*args, **kwargs)

    def __str__(self):
        return self.package_name


class Rice(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    cuisine = models.ForeignKey(Cuisine, on_delete=models.CASCADE, null=True)
    extra_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    default = models.BooleanField(default=False)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True, blank=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['package', 'cuisine'], name='unique_rice')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(Rice, self).save(*args, **kwargs)


class MainCuisine(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    cuisine = models.ForeignKey(Cuisine, on_delete=models.CASCADE)
    porsi = models.IntegerField(default=0)
    extra_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    default = models.BooleanField(default=False)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True, blank=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['package', 'cuisine'], name='unique_main_cuisine')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(MainCuisine, self).save(*args, **kwargs)


class SubCuisine(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    cuisine = models.ForeignKey(Cuisine, on_delete=models.CASCADE)
    porsi = models.IntegerField(default=0)
    extra_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    default = models.BooleanField(default=False)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True, blank=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['package', 'cuisine'], name='unique_sub_cuisine')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(SubCuisine, self).save(*args, **kwargs)


class SideCuisine1(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    cuisine = models.ForeignKey(Cuisine, on_delete=models.CASCADE)
    extra_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    default = models.BooleanField(default=False)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True, blank=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['package', 'cuisine'], name='unique_side1_cuisine')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(SideCuisine1, self).save(*args, **kwargs)


class SideCuisine2(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    cuisine = models.ForeignKey(Cuisine, on_delete=models.CASCADE)
    extra_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    default = models.BooleanField(default=False)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True, blank=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['package', 'cuisine'], name='unique_side2_cuisine')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(SideCuisine2, self).save(*args, **kwargs)


class SideCuisine3(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    cuisine = models.ForeignKey(Cuisine, on_delete=models.CASCADE)
    extra_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    default = models.BooleanField(default=False)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True, blank=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['package', 'cuisine'], name='unique_side3_cuisine')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(SideCuisine3, self).save(*args, **kwargs)


class SideCuisine4(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    cuisine = models.ForeignKey(Cuisine, on_delete=models.CASCADE)
    extra_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    default = models.BooleanField(default=False)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True, blank=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['package', 'cuisine'], name='unique_side4_cuisine')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(SideCuisine4, self).save(*args, **kwargs)


class SideCuisine5(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    cuisine = models.ForeignKey(Cuisine, on_delete=models.CASCADE)
    extra_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    default = models.BooleanField(default=False)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True, blank=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['package', 'cuisine'], name='unique_side5_cuisine')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(SideCuisine5, self).save(*args, **kwargs)


class Bag(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    extra_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    default = models.BooleanField(default=False)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True, blank=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['package', 'equipment'], name='unique_bag')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(Bag, self).save(*args, **kwargs)


class Beverage(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    extra_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    default = models.BooleanField(default=False)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True, blank=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['package', 'equipment'], name='unique_drink')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(Beverage, self).save(*args, **kwargs)


class Other(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    extra_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    default = models.BooleanField(default=False)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True, blank=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['package', 'equipment'], name='unique_other')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(Other, self).save(*args, **kwargs)


class Souvenir(models.Model):
    package = models.ForeignKey(
        Package, on_delete=models.CASCADE, null=True, default=None)
    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE, null=True, default=None)
    extra_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    default = models.BooleanField(default=False)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True, blank=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['package', 'equipment'], name='unique_souvenir')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().username
        self.update_date = timezone.now()
        self.update_by = get_current_user().username
        super(Souvenir, self).save(*args, **kwargs)


class Pack(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    extra_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    default = models.BooleanField(default=False)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True, blank=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['package', 'equipment'], name='unique_pack')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(Pack, self).save(*args, **kwargs)


class Addon(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    extra_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    default = models.BooleanField(default=False)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True, blank=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['package', 'equipment'], name='unique_addon')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().username
        super(Addon, self).save(*args, **kwargs)


class AreaSales(models.Model):
    area_id = models.CharField(max_length=50, primary_key=True)
    area_name = models.CharField(max_length=50)
    manager = models.CharField(max_length=50)
    bank_account = models.CharField(max_length=200, null=True)
    address = models.CharField(max_length=200, null=True)
    district = models.CharField(max_length=50, null=True)
    city = models.CharField(max_length=50, null=True)
    postal_code = models.CharField(max_length=10, null=True)
    form = models.CharField(max_length=200, null=True)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True)
    update_by = models.CharField(max_length=50, null=True)

    def save(self, *args, **kwargs):
        self.area_id = self.area_id.upper()
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(AreaSales, self).save(*args, **kwargs)

    def __str__(self):
        return self.area_name

    def get_area_sales_children(self):
        return self.areasalesdetail_set.all()


class AreaUser(models.Model):
    area = models.ForeignKey(AreaSales, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True)
    update_by = models.CharField(max_length=50, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['area', 'user'], name='unique_area_user')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(AreaUser, self).save(*args, **kwargs)

    def __str__(self):
        return self.area_id


class Position(models.Model):
    position_id = models.CharField(
        max_length=3, primary_key=True, help_text='Max 3 digits Position shortname.')
    position_name = models.CharField(max_length=50)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True)
    update_by = models.CharField(max_length=50, null=True)

    def save(self, *args, **kwargs):
        self.position_id = self.position_id.upper()
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(Position, self).save(*args, **kwargs)

    def __str__(self):
        return self.position_name


class Menu(models.Model):
    menu_id = models.CharField(max_length=50, primary_key=True)
    menu_name = models.CharField(max_length=50)
    menu_remark = models.CharField(max_length=200, null=True, blank=True)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True)
    update_by = models.CharField(max_length=50, null=True)

    def save(self, *args, **kwargs):
        self.menu_id = self.menu_id.upper()
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(Menu, self).save(*args, **kwargs)

    def __str__(self):
        return self.menu_name


class Auth(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE)
    add = models.BooleanField(default=False)
    edit = models.BooleanField(default=False)
    delete = models.BooleanField(default=False)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(null=True)
    update_by = models.CharField(max_length=50, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'menu'], name='unique_user_menu')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(Auth, self).save(*args, **kwargs)

    def __str__(self):
        return self.menu.menu_name


class Region(models.Model):
    region_id = models.CharField(max_length=50, primary_key=True)
    region_name = models.CharField(max_length=50)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(
        null=True, blank=True, auto_now=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.region_id = self.region_id.upper()
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().username
        self.update_date = timezone.now()
        self.update_by = get_current_user().username
        super(Region, self).save(*args, **kwargs)

    def __str__(self):
        return self.region_name


class RegionDetail(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    area = models.ForeignKey(AreaSales, on_delete=models.CASCADE)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(
        null=True, blank=True, auto_now=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['region', 'area'], name='unique_region_area')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.update_by = get_current_user().username
        self.update_date = timezone.now()
        self.update_by = get_current_user().username
        super(RegionDetail, self).save(*args, **kwargs)


class Customer(models.Model):
    customer_id = models.BigAutoField(primary_key=True)
    customer_name = models.CharField(max_length=200)
    customer_address = models.CharField(max_length=200, null=True)
    customer_district = models.CharField(max_length=50, null=True)
    customer_city = models.CharField(max_length=50, null=True)
    customer_province = models.CharField(max_length=50, null=True)
    customer_phone = models.CharField(max_length=50, null=True)
    customer_phone2 = models.CharField(max_length=50, null=True)
    customer_email = models.CharField(max_length=50, null=True)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(
        null=True, blank=True, auto_now=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(Customer, self).save(*args, **kwargs)


class CustomerDetail(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    child_name = models.CharField(max_length=200)
    child_birth = models.DateField(null=True)
    child_sex = models.CharField(max_length=1, null=True)
    child_father = models.CharField(max_length=200, null=True)
    child_mother = models.CharField(max_length=200, null=True)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(
        null=True, blank=True, auto_now=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['customer', 'child_name'], name='unique_customer_child')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(CustomerDetail, self).save(*args, **kwargs)


class BoxType(models.Model):
    box_type_id = models.BigAutoField(primary_key=True)
    box_type_name = models.CharField(max_length=50)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(
        null=True, blank=True, auto_now=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(BoxType, self).save(*args, **kwargs)

    def __str__(self):
        return self.box_type_name


class Order(models.Model):
    order_id = models.CharField(max_length=50, primary_key=True)
    regional = models.ForeignKey(
        AreaSales, on_delete=models.CASCADE, null=True)
    order_date = models.DateTimeField(null=True)
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=50, null=True)
    customer_phone2 = models.CharField(max_length=50, null=True)
    customer_email = models.CharField(max_length=50, null=True)
    customer_address = models.CharField(max_length=200, null=True)
    customer_district = models.CharField(max_length=50, null=True)
    customer_city = models.CharField(max_length=50, null=True)
    customer_province = models.CharField(max_length=50, null=True)
    delivery_date = models.DateTimeField(null=True)
    time_arrival = models.CharField(max_length=50, null=True)
    total_order = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    down_payment = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    discount = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    pending_payment = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    promo = models.CharField(max_length=50, null=True)
    promo_nominal = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    use_photo = models.BooleanField(default=False)
    witnessed = models.BooleanField(default=False)
    info_source = models.CharField(max_length=50, null=True)
    order_note = models.CharField(max_length=200, null=True)
    cs = models.CharField(max_length=50, null=True)
    order_status = models.CharField(max_length=15, default='PENDING')
    driver = models.CharField(max_length=100, null=True, blank=True)
    departure_time = models.CharField(max_length=10, default='00:00')
    schedule_status = models.CharField(max_length=20, default='UNSCHEDULED')
    seq_number = models.IntegerField(default=0)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(
        null=True, blank=True, auto_now=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.pending_payment = self.total_order - self.down_payment - self.discount

        if self.pk:
            try:
                old = Order.objects.get(pk=self.pk)
                if old.delivery_date != self.delivery_date:
                    self.schedule_status = 'UNSCHEDULED'
                    self.driver = None
                    self.departure_time = '00:00'
            except Order.DoesNotExist:
                pass

        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = 'customer'
        self.update_date = timezone.now()
        self.update_by = 'customer'
        super(Order, self).save(*args, **kwargs)


class OrderChild(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    child_name = models.CharField(max_length=200)
    child_birth = models.DateField(null=True)
    child_sex = models.CharField(max_length=1, null=True)
    child_father = models.CharField(max_length=200, null=True)
    child_mother = models.CharField(max_length=200, null=True)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(
        null=True, blank=True, auto_now=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'child_name'], name='unique_order_child')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = 'customer'
        self.update_date = timezone.now()
        self.update_by = 'customer'
        super(OrderChild, self).save(*args, **kwargs)


class OrderPackage(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True)
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    type = models.CharField(max_length=10, null=True)
    quantity = models.IntegerField(default=1)
    box_qty = models.IntegerField(default=1, null=True)
    box_type = models.CharField(max_length=50, null=True)
    main_cuisine = models.CharField(max_length=50, null=True)
    main_cuisine_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    sub_cuisine = models.CharField(max_length=50, null=True)
    side_cuisine1 = models.CharField(max_length=50, null=True)
    side_cuisine2 = models.CharField(max_length=50, null=True)
    side_cuisine3 = models.CharField(max_length=50, null=True)
    side_cuisine4 = models.CharField(max_length=50, null=True)
    side_cuisine5 = models.CharField(max_length=50, null=True)
    rice = models.CharField(max_length=50, null=True)
    bag = models.CharField(max_length=50, null=True)
    beverage = models.CharField(max_length=50, null=True)
    souvenir = models.CharField(max_length=50, null=True, default='')
    upgrade = models.TextField(null=True, blank=True)
    extra_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    total_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(
        null=True, blank=True, auto_now=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'package'], name='unique_order_package')
        ]

    def save(self, *args, **kwargs):
        self.total_price = (Decimal(self.quantity) *
                            self.unit_price) + self.extra_price
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = 'customer'
        self.update_date = timezone.now()
        self.update_by = 'customer'
        super(OrderPackage, self).save(*args, **kwargs)


class OrderLeftoverFood(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True)
    leftover_food = models.CharField(max_length=50, null=True)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(
        null=True, blank=True, auto_now=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'package', 'leftover_food'], name='unique_order_leftover_food')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(OrderLeftoverFood, self).save(*args, **kwargs)


class OrderPackageSouvenir(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE, null=True)
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    quantity = models.IntegerField(default=1)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(
        null=True, blank=True, auto_now=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'package', 'equipment'], name='unique_order_package_souvenir')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = 'customer'
        self.update_date = timezone.now()
        self.update_by = 'customer'
        super(OrderPackageSouvenir, self).save(*args, **kwargs)


class OrderPackageAddon(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE, null=True)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    total_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(
        null=True, blank=True, auto_now=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'package', 'equipment'], name='unique_order_package_addon')
        ]

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = 'customer'
        self.update_date = timezone.now()
        self.update_by = 'customer'
        super(OrderPackageAddon, self).save(*args, **kwargs)


class CashIn(models.Model):
    cashin_id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    cashin_date = models.DateTimeField(null=True)
    cashin_type = models.CharField(max_length=50, null=True)
    cashin_amount = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    cashin_note = models.CharField(max_length=200, null=True)
    bank = models.CharField(max_length=50, null=True)
    evidence = models.FileField(upload_to='cashin/', null=True)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(
        null=True, blank=True, auto_now=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(CashIn, self).save(*args, **kwargs)


class Promo(models.Model):
    promo_id = models.BigAutoField(primary_key=True)
    promo_name = models.CharField(max_length=200)
    promo_limit = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(
        null=True, blank=True, auto_now=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(Promo, self).save(*args, **kwargs)


class PromoDetail(models.Model):
    promo = models.ForeignKey(Promo, on_delete=models.CASCADE)
    gift = models.CharField(max_length=50)
    nominal = models.DecimalField(
        max_digits=12, decimal_places=0, default=0)
    entry_date = models.DateTimeField(null=True)
    entry_by = models.CharField(max_length=50, null=True)
    update_date = models.DateTimeField(
        null=True, blank=True, auto_now=True)
    update_by = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['promo', 'gift'], name='unique_promo_gift')
        ]

    def save(self, *args, **kwargs):
        if not self.entry_date:
            self.entry_date = timezone.now()
            self.entry_by = get_current_user().user_id
        self.update_date = timezone.now()
        self.update_by = get_current_user().user_id
        super(PromoDetail, self).save(*args, **kwargs)
