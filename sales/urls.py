from django.conf.urls import url
from sales import views

urlpatterns = [
    url(r'^company/$', views.CompanyList.as_view(), name='all_company'),
    url(r'^ajax_add_company/$', views.companyadd, name='ajax_add_company'),
    url(r'^ajax_add_contact_company/$', views.contactCompanyAdd, name='ajax_add_contact_company'),
    url(r'^ajax_get_company/$', views.getCompany, name='ajax_get_company'),
    url(r'^ajax_delete_company/$', views.companydelete, name='ajax_delete_company'),
    url(r'^ajax_all_company/$', views.ajax_companys, name='ajax_all_company'),
    url(r'^ajax_filter_company/$', views.ajax_companys_filter, name='ajax_filter_company'),
    url(r'^ajax-export-company/$', views.ajax_export_company, name='ajax-export-company'),
    url(r'^ajax-import-company/$', views.ajax_import_company, name='ajax-import-company'),

    #contact part
    url(r'^contact/$', views.ContactList.as_view(), name='all_contact'),
    url(r'^ajax_add_contact/$', views.contactadd, name='ajax_add_contact'),
    url(r'^ajax_get_contact/$', views.getContact, name='ajax_get_contact'),
    url(r'^ajax_all_contact/$', views.ajax_contacts, name='ajax_all_contact'),
    url(r'^ajax_filter_contact/$', views.ajax_contacts_filter, name='ajax_filter_contact'),
    url(r'^ajax_delete_contact/$', views.contactdelete, name='ajax_delete_contact'),
    url(r'^ajax-export-contact/$', views.ajax_export_contact, name='ajax-export-contact'),
    url(r'^ajax-import-contact/$', views.ajax_import_contact, name='ajax-import-contact'),

    #quotation part
    url(r'^quotation/$', views.QuotationList.as_view(), name='all_quotation'),
    url(r'^ajax_add_quotation/$', views.quotationadd, name='ajax_add_quotation'),
    url(r'^ajax_get_quotation/$', views.getQuotation, name='ajax_get_quotation'),
    url(r'^ajax_delete_quotation/$', views.quotationdelete, name='ajax_delete_quotation'),
    url(r'^ajax_read_notify/$', views.readnotify, name='ajax_read_notify'),
    url(r'^ajax_all_read_notify/$', views.markUserNotificationsRead, name='ajax_all_read_notify'),
    url(r'^quotation-detail/(?P<pk>[0-9]+)/$', views.QuotationDetailView.as_view(), name='quotation_detail'),
    url(r'^ajax_update_quotation/$', views.UpdateQuotation, name='ajax_update_quotation'),
    url(r'^ajax_update_quotation_override/$', views.UpdateQuotationOverride, name='ajax_update_quotation_override'),
    url(r'^ajax_check_quotation/$', views.check_quotation_number, name='ajax_check_quotation'),
    url(r'^ajax_check_quotation_company/$', views.check_quotation_company, name='ajax_check_quotation_company'),
    url(r'^ajax_check_quotation_contactperson/$', views.check_quotation_contact, name='ajax_check_quotation_contactperson'),
    url(r'^ajax_all_quotation/$', views.ajax_quotations, name='ajax_all_quotation'),
    url(r'^ajax_filter_quotation/$', views.ajax_quotations_filter, name='ajax_filter_quotation'),
    url(r'^export_quotation_pdf/(?P<value>\w+)/$', views.exportQuotationPDF, name='export_quotation_pdf'),
    url(r'^export_quotation_excel/(?P<value>\w+)/$', views.exportExcelQuotation, name='export_quotation_excel'),
    url(r'^ajax_add_scope_detail/$', views.scopeadd, name='ajax_add_scope_detail'),
    url(r'^ajax_get_scope/$', views.getScope, name='ajax_get_scope'),
    url(r'^ajax_get_file/$', views.getFile, name='ajax_get_file'),
    url(r'^ajax_delete_scope/$', views.scopedelete, name='ajax_delete_scope'),
    url(r'^ajax_delete_qfile/$', views.qfiledelete, name='ajax_delete_qfile'),
    url(r'^ajax_save_signature/$', views.signaturesave, name='ajax_save_signature'),
    url(r'^ajax_add_qfile/$', views.qfileadd, name='ajax_add_qfile'),
    url(r'^ajax_filter_person/$', views.ajax_filter_person, name='ajax_filter_person'),

    #Report part
    url(r'^report/$', views.ReportView.as_view(), name='all_reports'),
    url(r'^ajax-add-report/$', views.salereportadd, name='ajax_add_report'),
    url(r'^ajax_get_report_summary/$', views.getReport, name='ajax_get_report_summary'),
    url(r'^ajax_delete_report$', views.reportdelete, name='ajax_delete_report'),
    url(r'^report-detail/(?P<pk>[0-9]+)/$', views.ReportDetailView.as_view(), name='report_detail'),
    url(r'^ajax_update_report/$', views.UpdateReport, name='ajax_update_report'),
    url(r'^ajax_comment/$', views.addSaleComment, name='ajax_comment'),
    url(r'^ajax_get_comment/$', views.getComReport, name='ajax_get_comment'),
    url(r'^ajax_all_report/$', views.ajax_reports, name='ajax_all_report'),
    url(r'^ajax_filter_report/$', views.ajax_filter_report, name='ajax_filter_report'),
    url(r'^ajax_delete_comment/$', views.reportcommentdelete, name='ajax_delete_comment'),
]
