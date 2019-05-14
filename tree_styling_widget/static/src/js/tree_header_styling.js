// odoo.define('tree_header_styling', function(require) {
//     'use strict';
//
//     /**
//      * Unlike giving style to a cell, decorating a column title is more straight forward.
//      * First, we can determine which title to decorate by give the $th parameter only.
//      * As no extra condition is required, the attribute can be as simple as '{"css attribute": "style to applied"}'
//      *
//      * Logic: Get the $th data ( data of the column titles ) to determine where to apply the style. Use pyeval.py_eval()
//      *        to convert {"css attribute": "style to applied"} from string to dictionary. The key and value is then
//      *        pass to $th.css() as parameters.
//      */
//     let ListRenderer = require('web.ListRenderer');
//     var pyeval = require('web.pyeval');
//
//     ListRenderer.include({
//         _renderHeaderCell: function (node) {
//
//             var $th = this._super.apply(this, arguments);
//             this.header_style($th, node);
//             return $th;
//         },
//
//         header_style: function ($th, node) {
//
//             if (!node.attrs.headstyle) {return;}
//             if (node.tag !== 'field') {return;}
//
//             var nodeHS = node.attrs.headstyle;
//
//             if (_.isObject(nodeHS)) {
//                 nodeHS = JSON.stringify(nodeHS);
//                 nodeHS = pyeval.py_eval(nodeHS);
//             } else if (!_.isObject(nodeHS)) {
//                 nodeHS = pyeval.py_eval(nodeHS);
//             }
//
//             for ( var cssAttr in nodeHS) {
//                 var style = nodeHS[cssAttr];
//                 $th.css(cssAttr, style);
//             }
//         }
//     });
// });