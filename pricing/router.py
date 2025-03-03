class PricingRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'pricing':
            return 'default'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'pricing':
            return 'default'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._meta.app_label == 'pricing' or obj2._meta.app_label == 'pricing':
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'pricing':
            return False  # Prevent migrations since tables already exist
        return None
