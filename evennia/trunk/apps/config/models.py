from django.db import models

class CommandAlias(models.Model):
   """
   Command aliases.
   """
   user_input = models.CharField(maxlength=50)
   equiv_command = models.CharField(maxlength=50)
   
   class Admin:
      list_display = ('user_input', 'equiv_command',)

class ConfigValue(models.Model):
   """
   Experimental new config model.
   """
   conf_key = models.CharField(maxlength=100)
   conf_value = models.CharField(maxlength=255  )
   
   class Admin:
      list_display = ('conf_key', 'conf_value',)
