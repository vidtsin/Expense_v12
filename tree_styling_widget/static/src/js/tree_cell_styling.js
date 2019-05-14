odoo.define('tree_cell_styling', function(require){
    'use strict';

    let ListRenderer = require('web.ListRenderer');
    var pyeval = require('web.pyeval');
    var requiredHead = [];

    ListRenderer.include({
        /**
         * If the list has no records at all, _renderBodyCell() and the rest of the functions will not run. This
         * left elements in requiredHead list unshifted and alter css application for next list rendering.
         * For Odoo list rendering mechanism, an empty list must have 3 empty rows in order to make it look like
         * a list. Therefore, the list is emptied when empty rows are rendered.
         *
         */
        _renderEmptyRow: function(){
           this._super.apply(this, arguments);
           requiredHead = [];
        },

        /**
         * @Override
         * Original ListRenderer function to get header cell data.
         *
         */
        _renderHeaderCell: function (node) {
            var $th = this._super.apply(this, arguments);
            this.headChecker(node, $th);
            return $th;
        },

        /**
         * Store the $th (data of header cells) with headstyles node in a list as these header cells need style.
         * The global variable headIndex is used to iterate through this list.
         * Not a good practice to use global variable.
         */
        headChecker: function (node, headData) {
            if (node.tag !== 'field') {return;}
            if (node.attrs.headstyle) {
                requiredHead.push(headData);
            }
        },

        /**
         * Colorize a cell during it's render
         * @override
         * record is the record of a row and record.data is all the fields and the corresponding values
         * node = the field names contained in a tree view
         * colIndex = column number, from 0 to infinity
         * $td is the td class definition of each cell containing the value to be displayed in that cell
         * arguments = all the function arguments
         */
        _renderBodyCell: function (record, node, colIndex, options) {
            var $td = this._super.apply(this, arguments);
            var ctx = record.data;
            ctx = _.extend(ctx, {"True":true, "False": false, "true": true, "false": false});
            this.Styling($td, node, ctx);
            return $td;
        },

        /**
         * Apply styles to the current cell depending on expressions provided.
         * Will return if no styles, headstyle or context attributes in field node.
         *
         * @param {Query Node} $td a <td> tag inside a table representing a list view
         * @param {Object} node an XML node (must be a <field>)
         *
         * the css() serves as a translator to convert the line on the xml page to css language p.s.:From jquery.js
         *
         * node.attrs.styles = style attr in field node
         * node.attrs.context = context attr in field node
         * node.attrs.headstyle = headstyle attr in field node
         *
         * _.extend() adds the properties of nodeContext to the ctx.
         *
         * Source: https://github.com/OCA/web/tree/11.0/web_tree_dynamic_colored_field
         */
        Styling: function ($td, node, ctx) {
            if (node.tag !== 'field') { return; }  // no nodes other than field node are required
            if (node.attrs.styles) { var nodeStyles = this.dictConverter(node.attrs.styles); }
            if (node.attrs.headstyle) { var nodeHS = this.dictConverter(node.attrs.headstyle); }
            if (node.attrs.context) {
                var nodeContext = this.dictConverter(node.attrs.context);
                ctx = _.extend(ctx, nodeContext);
            }
            if (!nodeStyles && !nodeHS){ return; }

            if (nodeStyles) { // give style to cells
                for (var cssAttrC in nodeStyles) {
                    this.StylingHelper($td, nodeStyles, cssAttrC, ctx);
                }
            }

            if (nodeHS) { // give styles to header
                for (var cssAttrH in nodeHS) {
                    this.StylingHelper(requiredHead[0], nodeHS, cssAttrH, ctx);
                }
            }

        },

        /**
         * This function ensure the node attributes are in type of string.
         * py_eval() is an Odoo built-in function to convert strings in dict format to real dictionaries
         *
         */
        dictConverter: function (input){
            if (_.isObject(input)) {
                input = JSON.stringify(input); // from object to string
            }
            if (input !== undefined){
                input = pyeval.py_eval(input); // from string to dictionary
                return input;
            } else {
                return undefined; // if node attr is empty, which is not likely to happen
            }
        },

        /**cA is originally a string and a string is NOT supposed to be an object (== w/o properties)
         *
         * _.split() tries to access the properties of cA and JavaScript coerces the string values
         * to an object by the function: new String(str)
         * lodash.js _(str).split() != str.split()
         * This object is a wrapper object
         * doc: https://javascriptrefined.io/the-wrapper-object-400311b29151
         *
         * .chain() => to chain up the elements produced by .split()
         * .map(this.pairStyles) => map pairStyles() and put each element above into the fx for evaluation
         * .value() => return the values from pairStyles()
         * .filter() => sort out the undefined values by CheckUndefined()
         * doc: https://lodash.com/docs/4.17.10#chain
         */
        StylingHelper: function ($data, nodeAttribute, cssAttribute, ctx) {

            if ($data === undefined) { return; }
            // undefined $th will go down to the .css() causing error (as the condition is still true)
            // $td won't have this problem
            if ($data['0']['tagName'] === "TH") {
                requiredHead.shift();
                // the $th parameter should be shifted from the list after use to avoid confusion to the program
            }
            if (nodeAttribute[cssAttribute]) {
                var styles = _(nodeAttribute[cssAttribute].split(';'))
                    .chain()
                    .map(this.pairStyles)
                    .value()
                    .filter(function CheckUndefined(value) {
                        return value !== undefined;
                    });
                // styles is an array of nested arrays
                // eg. styles = [ ['red', "customer == A"],  ['green', "customer == A"] ]
                for (var i = 0, len = styles.length; i < len; ++i) {
                    var pair = styles[i], //pair is one of the array of the array of array
                        style = pair[0], //pair[0] = styling command
                        expression = pair[1]; //pair[1] = expression

                    if (py.evaluate(py.parse(py.tokenize(expression)), ctx).toJSON()) {
                        $data.css(cssAttribute, style);
                    }

                }
            }
        },

        /**
         * Parse `<style>: <field> <operator> <value>` forms to evaluable expressions
         *
         * @param {string} pairStyles `style: expression` pair eg(red:customer==True)
         * By .map(this.pairStyles), nodeStyles[cssAttribute] is passed to pairStyles
         * Therefore, function (pairStyle) defines pairStyle = nodeStyles[cssAttribute]
         */
        pairStyles: function (pairStyle){
            if (pairStyle !== "") {
                var pairList = pairStyle.split(':'),
                    style = pairList[0],
                    expression = pairList[1]? pairList[1] : 'True'; //? == exist? if yes, then OK: if not, take True
                return [style, expression];
            }
            return undefined;
        },
    });
});