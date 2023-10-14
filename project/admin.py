from django.contrib import admin

# Register your models here.
from project.models import Project, OT, Bom, Team, BomLog, ProjectFile, Sr, Do, Pc, DOSignature

admin.site.register(Project)
admin.site.register(OT)
admin.site.register(Bom)
admin.site.register(BomLog)
admin.site.register(Team)
admin.site.register(ProjectFile)
admin.site.register(Sr)
admin.site.register(Do)
admin.site.register(Pc)
admin.site.register(DOSignature)
