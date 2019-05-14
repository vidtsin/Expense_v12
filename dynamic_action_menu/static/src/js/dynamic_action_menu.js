odoo.define('dynamic_action_menu', function(require) {
    'use strict';

    /**
     * The action menu is rendered by the sidebar javascript. The 'renderer' object can contain a actionItem node if
     * we add it to ListRenderer. One is supposed to add a context field in action for menu in the xml and actionItems
     * should be a list.
     *
     * We can put the desired action items to the actionItems list in the context and the items will be available for
     * that specific page
     *
     * Eg. action item needed
     *
     * <field name="context">{'actionItems': {'list':["Download Cash Report"],
     *                                        'form':["Other button"]}}
     *
     *
     * Eg. No action Items
     *
     * <field name="context">{'actionItems': {'list':[""],
     *                                        'form':[""]}}
     *
     * Eg. Remove 'Export'
     * <field name="context">{'actionItems': {'export':'false'}
     *
     * Otherwise, all the action menu items will be rendered
     **/

    let FormRenderer = require('web.FormRenderer');
    let ListRenderer = require('web.ListRenderer');
    let Sidebar = require('web.Sidebar');

    FormRenderer.include({
        init: function (parent, state, params) {
                console.log('form');
                this._super.apply(this, arguments);

                try {
                    var actionMenu = parent["action"]["context"]["actionItems"]["form"];
                    if (actionMenu)
                        this.actionItems = actionMenu;
                }
                catch(err) {}
                // }
            }
        });

    ListRenderer.include({
            init: function (parent, state, params) {
                console.log('list');
                this._super.apply(this, arguments);

                try {
                    var actionMenu = parent["action"]["context"]["actionItems"]["list"];
                    if (actionMenu)
                        this.actionItems = actionMenu;
                }
                catch(err) {}
                // }
            }
        });

    Sidebar.include({
        init: function (parent, options) {
            this._super.apply(this, arguments);
            if (options.actions) {
                this._addToolbarActions(parent,options.actions);
            }
        },
        _addToolbarActions: function (parent, toolbarActions) {
            var self = this;

            if (parent["renderer"] && parent["renderer"]["actionItems"]) {
                _.each(['print', 'action', 'relate'], function (type) {
                    if (type in toolbarActions) {
                        var actions = toolbarActions[type];
                        if (actions && actions.length) {
                            var actionArray = [];
                            for (var i = 0; i < actions.length; ++i) {
                                var customActions = parent["renderer"]["actionItems"]['action'];
                                // for (var j = 0; j < customActions.length; ++j) {
                                var actionItem = actions[i];
                                if (actionItem.name in customActions && customActions[actionItem.name] === true) {

                                    // var requiredItem = parent["renderer"]["actionItems"][j];
                                    // if (actionItem["name"] === requiredItem) {
                                    actionArray.push(
                                        {
                                            "label": actionItem.name,
                                            "action": actionItem
                                        }
                                    );

                                }
                            }
                            self._addItems(type === 'print' ? 'print' : 'other', actionArray);

                        }
                    }
                });
            var otherArray = [];
            var customOther = parent['renderer']['actionItems']['other'];
            for (var k = 0; k < toolbarActions.other.length; ++k) {
                var otherItems = toolbarActions.other[k];
                if (otherItems.label in customOther && customOther[otherItems.label] === true) {
                    otherArray.push(otherItems);
                }
            }
            self._addItems('other', otherArray);


            } else {
                this._super.apply(this, arguments);
            }
        }
    })
});
