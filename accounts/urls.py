from django.conf.urls import url
from accounts import views
from django.contrib.auth.views import PasswordResetView 
from django.contrib.auth.views import PasswordResetDoneView
from django.contrib.auth.views import PasswordResetConfirmView
from django.contrib.auth.views import PasswordResetCompleteView
from django.urls import reverse_lazy

urlpatterns = [
    url(r'^login/$', views.LoginView.as_view(), name='view_login'),
    url(r'^logout/$', views.LogoutView.as_view(), name='view_logout'),
    url(r'^signup/$', views.SignupView.as_view(), name='view_signup'),
    url(r'^reset/password/$', PasswordResetView.as_view(template_name='accounts/password_reset_form.html', email_template_name='accounts/password_reset_email.html'), name='password_reset'),
    url(r'^reset/password/reset/done/$', PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'), name='password_reset_done'),
    url(r'reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$', PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html',success_url=reverse_lazy('password_reset_complete')), name='password_reset_confirm'),
    url(r'^reset/done/$', PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'), name='password_reset_complete'),

    #User part
    url(r'^users/$', views.UsersList.as_view(), name='all_users'),
    url(r'^user-configuration/$', views.UsersConfiguration.as_view(), name='user_configuration'),
    url(r'^notification-configuration/$', views.NotificationConfiguration.as_view(), name='notification_configuration'),
    url(r'^notification-information/$', views.NotificationView.as_view(), name='notification_information'),
    url(r'^activate/(?P<uidb64>.+)/(?P<token>.+)/$',views.activateAccount, name='activateaccount'),
    url(r'^ajax_privilege/$', views.ajax_privilege, name='ajax_privilege'),
    url(r'^ajax_privilege_user_check/$', views.ajax_privilege_user_check, name='ajax_privilege_user_check'),
    url(r'^ajax_privilege_notification/$', views.ajax_notification_privilege, name='ajax_privilege_notification'),
    url(r'^ajax_notification_privilege_user_check/$', views.ajax_notification_privilege_user_check, name='ajax_notification_privilege_user_check'),
    url(r'^ajax_all_users/$', views.ajax_users, name='ajax_all_users'),
    url(r'^ajax_filter_user/$', views.ajax_users_filter, name='ajax_filter_user'),
    url(r'^ajax_add_cert/$', views.usercertadd, name='ajax_add_cert'),
    url(r'^ajax_add_issuetool/$', views.userissuetooladd, name='ajax_add_issuetool'),
    url(r'^ajax_add_issue_ppe/$', views.userissueppeadd, name='ajax_add_issue_ppe'),
    url(r'^ajax_update_user_signature/$', views.updateUserSignature, name='ajax_update_user_signature'),

    url(r'^ajax-add-role/$', views.ajaxaddRole, name='ajax_add_role'),
    url(r'^ajax_add_user/$', views.newUser, name='ajax_add_user'),
    url(r'^user-detail/(?P<pk>[0-9]+)/$', views.UserDetailView.as_view(), name='user_detail'),
    url(r'^ajax_detail_add_user$', views.UpdateUser, name='ajax_detail_add_user'),
    url(r'^ajax_get_user_signature/$', views.getUserSignature, name='ajax_get_user_signature'),

    #worklog part
    url(r'^work-log/$', views.WorkLogList.as_view(), name='all_worklog'),
    url(r'^ajax_all_worklog/$', views.ajax_worklog, name='ajax_all_worklog'),
    url(r'^ajax_filter_worklog/$', views.ajax_worklog_filter, name='ajax_filter_worklog'),
    url(r'^ajax_add_worklog/$', views.worklogadd, name='ajax_add_worklog'),
    url(r'^ajax_delete_worklog/$', views.worklogdelete, name='ajax_delete_worklog'),
    url(r'^ajax_get_worklog/$', views.getWorklog, name='ajax_get_worklog'),
    url(r'^ajax_get_project_name/$', views.ajax_get_project_name, name='ajax_get_project_name'),
    url(r'^ajax-export-worklog/$', views.ajax_export_worklog, name='ajax-export-worklog'),
    url(r'^ajax-import-woklog/$', views.ajax_import_worklog, name='ajax-import-woklog'),

    #material log part
    url(r'^material-logs/$', views.MateriallogList.as_view(), name='all_materiallog'),
    url(r'^ajax_all_materiallog/$', views.ajax_materiallog, name='ajax_all_materiallog'),
    url(r'^ajax_filter_materiallog/$', views.ajax_materiallog_filter, name='ajax_filter_materiallog'),
    url(r'^ajax_add_materiallog/$', views.materiallogadd, name='ajax_add_materiallog'),
    url(r'^ajax_delete_materiallog/$', views.materiallogdelete, name='ajax_delete_materiallog'),
    url(r'^ajax_get_materiallog/$', views.getMateriallog, name='ajax_get_materiallog'),

    #assets log part
    url(r'^asset-logs/$', views.AssetLogList.as_view(), name='all_assetlog'),
    url(r'^ajax_all_assetlog/$', views.ajax_assetlog, name='ajax_all_assetlog'),
    url(r'^ajax_filter_assetlog/$', views.ajax_assetlog_filter, name='ajax_filter_assetlog'),
    url(r'^ajax_add_assetlog/$', views.assetlogadd, name='ajax_add_assetlog'),
    url(r'^ajax_delete_assetlog/$', views.assetlogdelete, name='ajax_delete_assetlog'),
    url(r'^ajax_get_assetlog/$', views.getAssetlog, name='ajax_get_assetlog'),

    #ot calculation part

    url(r'^ot-calculation/$', views.OtcalculationList.as_view(), name='all_otcalculation'),
    url(r'^ajax_all_otcalculate/$', views.ajax_otcalculation, name='ajax_all_otcalculate'),
    url(r'^ajax_filter_otcalculate/$', views.ajax_otcalculation_filter, name='ajax_filter_otcalculate'),
    url(r'^ajax_add_otcalculate/$', views.otcalculationadd, name='ajax_add_otcalculate'),
    url(r'^ajax_delete_otcalculate/$', views.otcalculationdelete, name='ajax_delete_otcalculate'),
    url(r'^ajax_get_otcalculate/$', views.getOtcalculation, name='ajax_get_otcalculate'),
    url(r'^ot-calculation-summary/$', views.OtcalculationSummary.as_view(), name='ot_calculation_summary'),
    url(r'^ajax_summary_otcalculate/$', views.ajax_otcalculation_summary, name='ajax_summary_otcalculate'),
    url(r'^ot-calculation-filter-summary/(?P<checkin_time>[^/]+)/(?P<checkout_time>[^/]+)/$', views.OtcalculationFilterSummary.as_view(), name='ot_calculation_filter_summary'),
    url(r'^ajax_summary_filter_otcalculate/$', views.ajax_otcalculation_filter_summary, name='ajax_summary_filter_otcalculate'),

]
