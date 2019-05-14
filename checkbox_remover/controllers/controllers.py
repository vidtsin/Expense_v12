# -*- coding: utf-8 -*-
from odoo import http

# class CheckboxRemove(http.Controller):
#     @http.route('/checkbox_remove/checkbox_remove/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/checkbox_remove/checkbox_remove/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('checkbox_remove.listing', {
#             'root': '/checkbox_remove/checkbox_remove',
#             'objects': http.request.env['checkbox_remove.checkbox_remove'].search([]),
#         })

#     @http.route('/checkbox_remove/checkbox_remove/objects/<model("checkbox_remove.checkbox_remove"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('checkbox_remove.object', {
#             'object': obj
#         })