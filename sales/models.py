from django.db import models
from cities_light.models import Country
from accounts.models import Uom, User

def content_file_signature(instance, filename):
    return 'signature/{1}'.format(instance, filename)

def content_file(instance, filename):
    return 'quotation/%s/files/%s' % (instance.quotation.qtt_id, filename)

# Create your models here.
class Payment(models.Model):

    method = models.CharField(max_length=255, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.method
    class Meta:
        db_table = "tb_payment"

class Validity(models.Model):
    
    method = models.CharField(max_length=255, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.method
    class Meta:
        db_table = "tb_validity"

class Company(models.Model):
    Customer = 'Customer'
    Supplier = 'Supplier'
    Partner = 'Partner'
    Associate = (
        ('Customer', 'Customer'),
        ('Supplier', 'Supplier'),
        ('Partner', 'Partner'),
    )
    name = models.CharField(unique=True,max_length=150, blank=True, null=True)
    address = models.CharField(max_length=100, blank=True, null=True)
    unit = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.IntegerField(default=0)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, blank=True, null=True)
    validity = models.ForeignKey(Validity, on_delete=models.SET_NULL, blank=True, null=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, blank=True, null=True)
    associate = models.CharField(max_length=100, choices=Associate, default=Customer)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return self.name
    class Meta:
        db_table = "tb_company"
        ordering = ['id']

class Contact(models.Model):
    Mr = 'Mr'
    Salutation = (
        ('Mr', 'Mr'),
        ('Mrs', 'Mrs'),
        ('Ms', 'Ms'),
        ('Mdm', 'Mdm'),
        ('Dr', 'Dr'),
    )
    Director = 'Director'
    Role = (
        ('Director', 'Director'),
        ('Manager', 'Manager'),
        ('Purchaser', 'Purchaser'),
        ('Contract', 'Contract'),
        ('Sales', 'Sales'),
        ('Others', 'Others'),
    )
    contact_person = models.CharField(unique=True, max_length=100, blank=True, null=True)
    salutation = models.CharField(max_length=100, choices=Salutation, default=Mr)
    tel = models.CharField(max_length=150, blank=True, null=True)
    fax = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(max_length=250, blank=True, null=True)
    role = models.CharField(max_length=100, choices=Role, default=Director)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return self.contact_person
    class Meta:
        db_table = "tb_contact"

class Quotation(models.Model):
    Open = 'Open'
    Awarded = 'Awarded'
    Closed = 'Closed'
    Loss = 'Loss'
    Status = (
        ('Open', 'Open'),
        ('Awarded', 'Awarded'),
        ('Closed', 'Closed'),
        ('Loss', 'Loss'),
    )

    Project = 'Project'
    Maintenance = 'Maintenance'
    Sales = 'Sales'
    SaleType = (
        ('Project', 'Project'),
        ('Maintenance', 'Maintenance'),
        ('Sales', 'Sales'),
    )
    NA = "NA"
    LeadTime = (
        ('NA', 'NA'),
        ('TBA ', 'TBA '),
        ('Ex-stock', 'Ex-stock'),
        ('Ex-stock or 6 to 8 weeks', 'Ex-stock or 6 to 8 weeks'),
        ('Ex-stock or 8 to 12 weeks', 'Ex-stock or 8 to 12 weeks'),
        ('Ex-stock or 12 to 16 weeks', 'Ex-stock or 12 to 16 weeks'),
        ('3 to 4 weeks', '3 to 4 weeks'),
        ('6 to 8 weeks', '6 to 8 weeks'),
        ('8 to 12 weeks', '8 to 12 weeks'),
        ('12 to 16 weeks', '12 to 16 weeks'),
        ('16 to 20 weeks', '16 to 20 weeks'),
        
    )
    qtt_id = models.CharField(max_length=100, blank=True, null=True)
    company_name = models.ForeignKey(Company, on_delete=models.SET_NULL, blank=True, null=True)
    address = models.CharField(max_length=100, blank=True, null=True)
    unit = models.CharField(max_length=100, blank=True, null=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, blank=True, null=True)
    tel = models.CharField(max_length=50, blank=True, null=True)
    fax = models.CharField(max_length=50, blank=True, null=True)
    contact_person = models.ForeignKey(Contact, on_delete=models.SET_NULL, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    sale_type = models.CharField(max_length=100, choices=SaleType, default=Project)
    date = models.DateField(null=True, blank=True)
    qtt_status = models.CharField(max_length=100, choices=Status, default=Open)
    RE = models.TextField(null=True, blank=True)
    total = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    gst = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    finaltotal = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    note = models.TextField(null=True, blank=True)
    sale_person = models.CharField(max_length=100, blank=True, null=True)
    auth_signature = models.CharField(max_length=100, blank=True, null=True)
    estimated_mandays = models.CharField(max_length=100, blank=True, null=True)
    auth_name = models.CharField(max_length=100, blank=True, null=True)
    signature_date = models.DateField(null=True, blank=True)
    po_no = models.CharField(max_length=100, blank=True, null=True)
    validity = models.CharField(max_length=255, blank=True, null=True)
    terms = models.CharField(max_length=255, blank=True, null=True)
    flag = models.BooleanField(null=True, blank=True)
    material_leadtime = models.CharField(max_length=255, choices=LeadTime, default=NA, blank=True, null=True)

    def __str__(self):
        return self.qtt_id
    class Meta:
        db_table = "tb_quotation"

class SaleReport(models.Model):
    Open = 'Open'
    Awarded = 'Awarded'
    Closed = 'Closed'
    Loss = 'Loss'
    Status = (
        ('Open', 'Open'),
        ('Awarded', 'Awarded'),
        ('Closed', 'Closed'),
        ('Loss', 'Loss'),
    )

    Project = 'Project'
    Maintenance = 'Maintenance'
    Sales = 'Sales'
    SaleType = (
        ('Project', 'Project'),
        ('Maintenance', 'Maintenance'),
        ('Sales', 'Sales'),
    )
    qtt_id = models.CharField(unique=True, max_length=100, blank=True, null=True)
    company_name = models.ForeignKey(Company, on_delete=models.SET_NULL, blank=True, null=True)
    address = models.CharField(max_length=100, blank=True, null=True)
    unit = models.CharField(max_length=100, blank=True, null=True)
    postalcode = models.IntegerField(default=0)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, blank=True, null=True)
    contact_person = models.ForeignKey(Contact, on_delete=models.SET_NULL, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    finaltotal = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    sale_person = models.CharField(max_length=100, blank=True, null=True)
    RE = models.TextField(null=True, blank=True)
    qtt_status = models.CharField(max_length=100, choices=Status, default=Open)
    sale_type = models.CharField(max_length=100, choices=SaleType, default=Project)
    date = models.DateField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    comment_by = models.CharField(max_length=100, blank=True, null=True)
    comment_at = models.DateField(null=True, blank=True)
    quotation = models.ForeignKey(Quotation, on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return self.qtt_id
    class Meta:
        db_table = "tb_sale_report"

    
class SaleReportComment(models.Model):
    salereport = models.ForeignKey(SaleReport, on_delete=models.SET_NULL, blank=True, null=True)
    comment = models.TextField(null=True, blank=True)
    comment_by = models.CharField(max_length=100, blank=True, null=True)
    comment_at = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.comment_by

    class Meta:
        db_table = "tb_sale_report_comment"


class Scope(models.Model):
    qtt_id = models.CharField(max_length=100, blank=True, null=True)
    sn = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    qty = models.IntegerField(null=True, blank=True, default=0)
    uom = models.ForeignKey(Uom, on_delete=models.SET_NULL, blank=True, null=True)
    unitprice = models.DecimalField(max_digits=20, decimal_places=2,default=0, null=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2,default=0, null=True)
    bal_qty = models.IntegerField(null=True, blank=True, default=0)
    allocation_perc = models.CharField(max_length=50, blank=True, null=True)
    quotation = models.ForeignKey(Quotation, on_delete=models.SET_NULL, blank=True, null=True)
    parent = models.ForeignKey('self', blank=True, null=True, on_delete=models.SET_NULL, related_name='children')

    def __str__(self):
        return self.description

    class Meta:
        db_table = "tb_scope"

class Signature(models.Model):
    # auth_signature = models.ImageField(upload_to=content_file_signature, blank=True)
    signanture_name = models.CharField(max_length=100, blank=True, null=True)
    company_stamp = models.ImageField(upload_to=content_file_signature, blank=True)
    signature_date = models.DateField(null=True, blank=True)
    quotation = models.OneToOneField(Quotation, on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return self.signanture_name

    class Meta:
        db_table = "tb_signature"

class QFile(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    document = models.FileField(upload_to=content_file, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    quotation = models.ForeignKey(Quotation, on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "tb_qfile"