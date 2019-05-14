Dynamic Cell Styling (Tree View)
-----------------------------------------------------------------------------------------------------------------------------
Based on "web_tree_dynamic_colored_field.js" launched by the Odoo Community
doc: https://github.com/OCA/web/tree/11.0/web_tree_dynamic_colored_field

This module aims to add support for dynamically apply styles to fields in tree view according to data in the record.

It provides attributes on fields with the similar syntax as the colors attribute in tree tags.

Further, it provides a context attribute on field tags to allow users to take boolean and string as data .


New Features:
1/ Remove [color_field] attribute as its function duplicated that of Odoo decoration-X
2/ Amend the attributes of the field's options to real CSS-compatible attributes in tree view
3/ Add CSS basic styling functions
4/ Allow the module to apply styles to cell base on value of fields, including strings and boolean

Usage
1. Highlight the whole column

In the tree view declaration, put styles='{"color": "red: True"} attribute in the field tag:
...
<field name="arch" type="xml">
    <tree string="View name">
        ...
        <field name="name" styles='{"color": "red:True"}'/>
        ...
    </tree>
</field>
...
With this example, the whole column will have font color in red.

2. Use boolean as data

In the tree view declaration, put styles='{"background-color": "red: customer==True"} attribute in the field tag:
p.s. customer is a field name which store true/false as data
...
<field name="arch" type="xml">
    <tree string="View name">
        ...
        <field name="name" styles='{"background-color": "red: customer==True"}'/>
        ...
    </tree>
</field>
...

With this example, column which renders 'name' field with bold text.
In the tree view declaration, put styles='{"font-weight": "bold:customer==True"}' attribute in the field tag:

...
<field name="arch" type="xml">
    <tree string="View name">
        ...
        <field name="name1" styles='{"font-weight": "bold:customer==True"}'/>
        <field name="name2" styles='{"font-style": "italic:customer==True"}'/>
        ...
    </tree>
</field>
...

3. Use string as data

With this example, column which renders 'name' field will have background in orange if customer record is "Customer A".
In the tree view declaration, use a new variable "A" in the options attribute and use context attribute to define the variable

...
<field name="arch" type="xml">
    <tree string="View name">
        ...
        <field name="name" styles='{"background-color": "orange:customer==A"}' context='{"A": "Customer A"}'/>
        ...
    </tree>
</field>
...


If you want to use more than one color, you can split the attributes using ';':

styles='{"color": "red:A==True; green:B==True",
          "background-color": "white:C==foo; black:D==bar"}'

context='{"foo": "str1", "bar":"str2"}


Example:

...
 <field name="arch" type="xml">
     <tree string="View name">
         ...
         <field name="name" styles='{"color": "red:A==True; green:B==True",
          "background-color": "white:C==foo; black:D==bar"}' context='{"foo": "str1", "bar":"str2"}
         ...
     </tree>
 </field>
 ...

4. Give style to a column title

In the tree view declaration, put headstyle='{"color": "red:True"} attribute in the field tag:
Attribute format is the same as styles attribute and context is required when string type data is used.
...
 <field name="arch" type="xml">
     <tree string="View name">
         ...
         <field name="name" headstyle='{"color": "red:True"}
         ...
     </tree>
 </field>
...
