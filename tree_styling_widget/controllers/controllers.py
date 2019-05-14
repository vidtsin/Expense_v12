# -*- coding: utf-8 -*-
from odoo import http

# class CellColoringWidget(http.Controller):
#     @http.route('/cell_coloring_widget/cell_coloring_widget/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/cell_coloring_widget/cell_coloring_widget/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('cell_coloring_widget.listing', {
#             'root': '/cell_coloring_widget/cell_coloring_widget',
#             'objects': http.request.env['cell_coloring_widget.cell_coloring_widget'].search([]),
#         })

#     @http.route('/cell_coloring_widget/cell_coloring_widget/objects/<model("cell_coloring_widget.cell_coloring_widget"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('cell_coloring_widget.object', {
#             'object': obj
#         })