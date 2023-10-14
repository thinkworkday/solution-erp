from django.contrib import admin
from sales.models import Company, SaleReport, SaleReportComment, Quotation, Contact, Scope, Signature, QFile, Payment, Validity
# Register your models here.

class CompanyAdmin(admin.ModelAdmin):
    model = Company

    list_display = ('name','address', 'unit', 'postal_code', 'country', 'associate')

admin.site.register(Company, CompanyAdmin)
admin.site.register(Quotation)
admin.site.register(SaleReport)
admin.site.register(SaleReportComment)
admin.site.register(Contact)
admin.site.register(Scope)
admin.site.register(Signature)
admin.site.register(QFile)
admin.site.register(Payment)
admin.site.register(Validity)