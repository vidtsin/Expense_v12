odoo.define('odoo_function_cell_coloring', function (require) {
    'use strict';
    // use strict: a strict mode for JS to be executed

    // var BasicRenderer = require('web.BasicRenderer');
    // var config = require('web.config');
    // var core = require('web.core');
    // var Dialog = require('web.Dialog');
    // var dom = require('web.dom');
    var field_utils = require('web.field_utils');
    // var Pager = require('web.Pager');
    // var utils = require('web.utils');

    var ListRenderer = require('web.ListRenderer'); // <== Call this JS
    var FIELD_CLASSES = {
    float: 'o_list_number',
    integer: 'o_list_number',
    monetary: 'o_list_number',
    text: 'o_list_text',
};
    // include all the modules needed in this JS


    ListRenderer.include({ //call the functions that required amendment and add new functions
        /**
         * Look up for a `color_field` parameter in tree `colors` attribute
         *
         * @override: by calling the same functions from the web.ListRenderer and write new lines to it, the original function will be overrode
         *
         */
        _renderRow: function (record) {
            var self = this;
            this.defs = []; // TODO maybe wait for those somewhere ?
            var $cells = _.map(this.columns, function (node, index) {
                return self._renderBodyCell(record, node, index, {mode: 'readonly'});
            });
            delete this.defs;

            var $tr = $('<tr/>', {class: 'o_data_row'})
                .data('id', record.id)
                .append($cells);
            if (this.hasSelectors) {
                $tr.prepend(this._renderSelector('td'));
            }
            // this._setDecorationClasses(record, $tr); <== this line is deleted from the original renderRow function
            // because if setDecorationClasses has $tr as a input, the whole row will be colored
            return $tr


        },
        /**
         * Colorize a cell during it's render
         *
         * @override
         */
        _renderBodyCell: function (record, node, colIndex, options) {
            var tdClassName = 'o_data_cell';
            if (node.tag === 'button') {
                tdClassName += ' o_list_button';
            } else if (node.tag === 'field') {
                var typeClass = FIELD_CLASSES[this.state.fields[node.attrs.name].type];
                if (typeClass) {
                    tdClassName += (' ' + typeClass);
                }
                if (node.attrs.widget) {
                    tdClassName += (' o_' + node.attrs.widget + '_cell');
                }
            }
            var $td = $('<td>', {class: tdClassName});

            // We register modifiers on the <td> element so that it gets the correct
            // modifiers classes (for styling)
            var modifiers = this._registerModifiers(node, record, $td, _.pick(options, 'mode'));
            // If the invisible modifiers is true, the <td> element is left empty.
            // Indeed, if the modifiers was to change the whole cell would be
            // rerendered anyway.
            if (modifiers.invisible && !(options && options.renderInvisible)) {
                return $td;
            }

            if (node.tag === 'button') {
                return $td.append(this._renderButton(record, node));
            } else if (node.tag === 'widget') {
                return $td.append(this._renderWidget(record, node));
            }
            if (node.attrs.widget || (options && options.renderWidgets)) {
                var widget = this._renderFieldWidget(node, record, _.pick(options, 'mode'));
                this._handleAttributes(widget.$el, node);
                return $td.append(widget.$el);
            }
            var name = node.attrs.name;
            var field = this.state.fields[name];
            var value = record.data[name];
            var formattedValue = field_utils.format[field.type](value, field, {
                data: record.data,
                escape: true,
                isPassword: 'password' in node.attrs,
            });
            this._handleAttributes($td, node);
            this._setDecorationClasses(record, $td, name); //call the coloring function and let it intakes $td(cell class) and the name of the field(for distinguishing)
            return $td.html(formattedValue);
        },

        /**
         * Colorize the current cell depending on expressions provided.
         *
         * @param {Query Node} $td a <td> tag inside a table representing a list view
         * @param {Object} node an XML node (must be a <field>)
         */

        _setDecorationClasses: function (record, $td, name) {
            //console.log(record, $td)
            _.each(this.rowDecorations, function (expr, decoration) {
                //console.log(expr)
                var cssClass = decoration.replace('decoration', 'text');
                if (name == expr["expressions"][0]["value"]) {
                    $td.toggleClass(cssClass, py.PY_isTrue(py.evaluate(expr, record.evalContext)));


    //_setDecorationClasses: function (record, $tr) {
    //     _.each(this.rowDecorations, function (expr, decoration) {
    //         var cssClass = decoration.replace('decoration', 'text');
    //         $tr.toggleClass(cssClass, py.PY_isTrue(py.evaluate(expr, record.evalContext)));
    //     });
    // },
                }
            });
        },
    });
});
