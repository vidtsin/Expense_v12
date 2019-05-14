odoo.define('checkbox_remove', function(require) {
    'use strict';

    let ListRenderer = require('web.ListRenderer');

    ListRenderer.include({
        init: function (parent, state, params) {
            /**
             * The logic below is only valid for list view.
             *
             * Odoo right now doesn't add any functions for the checkbox and hasSelectors (= checkbox existence) is
             * always true. We had find a way to turn this to false based on pages we are on .
             *
             * We somehow discovered that any custom context can be added to actions for menu in the xml file.
             * The context written can be found inside parent["action"]["context"]
             * The key and value below will be hasSelectors: false and the checkboxes are gone.
             * Eg.
             *
             * <-- Action for menu "Cash Expense details" -->
             * <record id="hhexpense_action_cash_expense_details" model="ir.actions.act_window">
             *     <field name="name">Cash Expenses Details</field>
             *     <field name="res_model">hhexpense.line</field>
             *     <field name="view_mode">tree,form</field>
             *     <field name="context">{'search_default_group_expense_emp_name_mst_id': 1,
             *                            'checkbox': False,]
             *                             }</field>
             * </record>
             *
             **/

            this._super.apply(this, arguments);
            if (parent["action"] == undefined) { return; }
            if (parent["action"]["context"] == undefined) { return; }
            else{
                if (parent["action"]["context"]["checkbox"] == false) {
                    this["hasSelectors"] = false;
                }
                }
            }
            // if (checkbox == 'false') {
            //     this["hasSelectors"] = false;
            // }else{
            //     this["hasSelectors"] = true;
            // }
        })
    });

