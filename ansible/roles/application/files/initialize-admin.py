# Executed only for a newly initialized database, via Odoo shell.
import os
admin=env.ref('base.user_admin')
admin.write({'login': 'admin', 'password': os.environ['ODOO_ADMIN_PASSWORD']})
env.cr.commit()
