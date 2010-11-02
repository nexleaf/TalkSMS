# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Clinician'
        db.create_table('taskmanager_clinician', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], unique=True)),
        ))
        db.send_create_signal('taskmanager', ['Clinician'])

        # Adding model 'Patient'
        db.create_table('taskmanager_patient', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('address', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=80)),
        ))
        db.send_create_signal('taskmanager', ['Patient'])

        # Adding M2M table for field clinicians on 'Patient'
        db.create_table('taskmanager_patient_clinicians', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('patient', models.ForeignKey(orm['taskmanager.patient'], null=False)),
            ('clinician', models.ForeignKey(orm['taskmanager.clinician'], null=False))
        ))
        db.create_unique('taskmanager_patient_clinicians', ['patient_id', 'clinician_id'])

        # Adding model 'Service'
        db.create_table('taskmanager_service', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100, db_index=True)),
            ('last_status', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('last_status_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('taskmanager', ['Service'])

        # Adding model 'AlertType'
        db.create_table('taskmanager_alerttype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100, db_index=True)),
            ('service', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['taskmanager.Service'])),
            ('title_template', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('message_template', self.gf('django.db.models.fields.TextField')()),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal('taskmanager', ['AlertType'])

        # Adding model 'Alert'
        db.create_table('taskmanager_alert', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('alert_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['taskmanager.AlertType'])),
            ('patient', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['taskmanager.Patient'], null=True, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('message', self.gf('django.db.models.fields.TextField')()),
            ('arguments', self.gf('django.db.models.fields.TextField')()),
            ('add_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('taskmanager', ['Alert'])

        # Adding model 'Task'
        db.create_table('taskmanager_task', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('module', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('className', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('schedulable', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('taskmanager', ['Task'])

        # Adding M2M table for field templates on 'Task'
        db.create_table('taskmanager_task_templates', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('task', models.ForeignKey(orm['taskmanager.task'], null=False)),
            ('template', models.ForeignKey(orm['dbtemplates.template'], null=False))
        ))
        db.create_unique('taskmanager_task_templates', ['task_id', 'template_id'])

        # Adding model 'TaskTemplate'
        db.create_table('taskmanager_tasktemplate', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('task', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['taskmanager.Task'])),
            ('arguments', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('taskmanager', ['TaskTemplate'])

        # Adding model 'Process'
        db.create_table('taskmanager_process', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('patient', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['taskmanager.Patient'])),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['taskmanager.Clinician'], null=True, blank=True)),
            ('add_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('taskmanager', ['Process'])

        # Adding model 'Session'
        db.create_table('taskmanager_session', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('patient', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['taskmanager.Patient'])),
            ('task', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['taskmanager.Task'])),
            ('process', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['taskmanager.Process'], null=True)),
            ('add_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('completed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('completed_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('timeout_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal('taskmanager', ['Session'])

        # Adding model 'SessionMessage'
        db.create_table('taskmanager_sessionmessage', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('session', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['taskmanager.Session'])),
            ('message', self.gf('django.db.models.fields.TextField')()),
            ('outgoing', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('add_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('taskmanager', ['SessionMessage'])

        # Adding model 'TaskPatientDatapoint'
        db.create_table('taskmanager_taskpatientdatapoint', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('patient', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['taskmanager.Patient'])),
            ('task', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['taskmanager.Task'])),
            ('add_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('data', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('taskmanager', ['TaskPatientDatapoint'])

        # Adding model 'ScheduledTask'
        db.create_table('taskmanager_scheduledtask', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('patient', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['taskmanager.Patient'])),
            ('task', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['taskmanager.Task'])),
            ('process', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['taskmanager.Process'], null=True)),
            ('add_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('arguments', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('schedule_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('completed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('completed_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('result', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('taskmanager', ['ScheduledTask'])


    def backwards(self, orm):
        
        # Deleting model 'Clinician'
        db.delete_table('taskmanager_clinician')

        # Deleting model 'Patient'
        db.delete_table('taskmanager_patient')

        # Removing M2M table for field clinicians on 'Patient'
        db.delete_table('taskmanager_patient_clinicians')

        # Deleting model 'Service'
        db.delete_table('taskmanager_service')

        # Deleting model 'AlertType'
        db.delete_table('taskmanager_alerttype')

        # Deleting model 'Alert'
        db.delete_table('taskmanager_alert')

        # Deleting model 'Task'
        db.delete_table('taskmanager_task')

        # Removing M2M table for field templates on 'Task'
        db.delete_table('taskmanager_task_templates')

        # Deleting model 'TaskTemplate'
        db.delete_table('taskmanager_tasktemplate')

        # Deleting model 'Process'
        db.delete_table('taskmanager_process')

        # Deleting model 'Session'
        db.delete_table('taskmanager_session')

        # Deleting model 'SessionMessage'
        db.delete_table('taskmanager_sessionmessage')

        # Deleting model 'TaskPatientDatapoint'
        db.delete_table('taskmanager_taskpatientdatapoint')

        # Deleting model 'ScheduledTask'
        db.delete_table('taskmanager_scheduledtask')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dbtemplates.template': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Template', 'db_table': "'django_template'"},
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_changed': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'taskmanager.alert': {
            'Meta': {'ordering': "['-add_date']", 'object_name': 'Alert'},
            'add_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'alert_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['taskmanager.AlertType']"}),
            'arguments': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'patient': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['taskmanager.Patient']", 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taskmanager.alerttype': {
            'Meta': {'object_name': 'AlertType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message_template': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['taskmanager.Service']"}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'title_template': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'taskmanager.clinician': {
            'Meta': {'object_name': 'Clinician'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'taskmanager.patient': {
            'Meta': {'object_name': 'Patient'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'clinicians': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['taskmanager.Clinician']", 'symmetrical': 'False'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '80'})
        },
        'taskmanager.process': {
            'Meta': {'object_name': 'Process'},
            'add_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['taskmanager.Clinician']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'patient': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['taskmanager.Patient']"})
        },
        'taskmanager.scheduledtask': {
            'Meta': {'object_name': 'ScheduledTask'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'add_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'arguments': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'completed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'completed_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'patient': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['taskmanager.Patient']"}),
            'process': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['taskmanager.Process']", 'null': 'True'}),
            'result': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'schedule_date': ('django.db.models.fields.DateTimeField', [], {}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['taskmanager.Task']"})
        },
        'taskmanager.service': {
            'Meta': {'object_name': 'Service'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_status': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'last_status_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'taskmanager.session': {
            'Meta': {'object_name': 'Session'},
            'add_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'completed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'completed_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'patient': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['taskmanager.Patient']"}),
            'process': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['taskmanager.Process']", 'null': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['taskmanager.Task']"}),
            'timeout_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'taskmanager.sessionmessage': {
            'Meta': {'object_name': 'SessionMessage'},
            'add_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'outgoing': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'session': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['taskmanager.Session']"})
        },
        'taskmanager.task': {
            'Meta': {'object_name': 'Task'},
            'className': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'schedulable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'templates': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['dbtemplates.Template']", 'symmetrical': 'False'})
        },
        'taskmanager.taskpatientdatapoint': {
            'Meta': {'object_name': 'TaskPatientDatapoint'},
            'add_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'patient': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['taskmanager.Patient']"}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['taskmanager.Task']"})
        },
        'taskmanager.tasktemplate': {
            'Meta': {'object_name': 'TaskTemplate'},
            'arguments': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['taskmanager.Task']"})
        }
    }

    complete_apps = ['taskmanager']
