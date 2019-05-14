# -*- coding: utf-8 -*-
from odoo import http

# class DynamicActionMenu(http.Controller):
#     @http.route('/dynamic_action_menu/dynamic_action_menu/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/dynamic_action_menu/dynamic_action_menu/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('dynamic_action_menu.listing', {
#             'root': '/dynamic_action_menu/dynamic_action_menu',
#             'objects': http.request.env['dynamic_action_menu.dynamic_action_menu'].search([]),
#         })

#     @http.route('/dynamic_action_menu/dynamic_action_menu/objects/<model("dynamic_action_menu.dynamic_action_menu"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('dynamic_action_menu.object', {
#             'object': obj
#         })