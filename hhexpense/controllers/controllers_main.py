# -*- coding: utf-8 -*-
import werkzeug
from datetime import date, datetime
import os
from odoo import http
from odoo.http import request


class Binary(http.Controller):
    # Making download file fit to FlexAccount format
    @http.route('/web/binary/generate_flexacc_txt_file', type='http', auth='public')
    def generate_flexacc_txt_file(self, **kwargs):
        # Purpose of this function:
            # 1.Obtain id data
            # 2.Obtain payment_approve_date data, will be putted in file
            # 3.Obtain analysis code
            # 4.Create a dictionary to store file format based on given FlexAccount database structure
            # 5.Generate file (write data)
            # 6.Download file
        print("hi, controller catch the 'Generate FlexAccount txt file' request")

        # 1.
        # Get selected master record's id
        # based on the file that created in "get_input_payment_approved_date" method
        ids = []
        selected_rec_id_file = open("./flexacc_intermediate_file_get_selected_rec_id.txt", "r", encoding="utf-8")
        for line in selected_rec_id_file:
            ids.append(line.replace('\n', ''))  # E.g. ids = ['110', '109']
        selected_rec_id_file.close()
        os.remove("./flexacc_intermediate_file_get_selected_rec_id.txt")

        # 2.
        # Get payment_approve_date for selected master records
        # based on the file that created in "auto_post_processing" method
        payment_approve_date = ''
        temp_file_get_payment_approve_date = open(
                                                "./flexacc_intermediate_file_get_selected_rec_payment_approve_date.txt",
                                                "r", encoding="utf-8"
                                                 )
        for line in temp_file_get_payment_approve_date:
            print("original payment approve date:", line)
            payment_approve_date = line.replace('\n', '')
        temp_file_get_payment_approve_date.close()
        os.remove("./flexacc_intermediate_file_get_selected_rec_payment_approve_date.txt")
        # example:   2018-08-15
        # position:  1234567890
        offset = "/"
        date_y_l = offset + payment_approve_date[:2]
        date_y_r = payment_approve_date[2:4]
        date_m = payment_approve_date[5:7]
        date_d = payment_approve_date[-2:]

        # 3.
        # this code is depends on employee team
        # analysis_code = "90302"
        analysis_code = ""

        # 4.
        format_dic = {
            "Voucher Type": 2,
            "Voucher Ref": 10,
            "Voucher Date dd": 2,
            "Offset voucher Date dd": 1,
            "Voucher date mm": 2,
            "Offset voucher date mm": 3,
            "Voucher date yy": 2,
            "A / C": 10,
            "Analysis code 1": 3,
            "Analysis code 2": 3,
            "Analysis code 3": 5,
            "Analysis code 4": 3,
            "Analysis code 5": 6,
            "Currency": 3,
            "Amount": 16,
            "Exchange rate": 12,
            "Equv.amount": 16,
            "D / C sign": 1,
            "Document no.": 10,
            "Document type": 1,
            "Document date dd": 2,
            "Offset document date dd": 1,
            "Document date mm": 2,
            "Offset document date mm": 3,
            "Document date yy": 2,
            "Payment term": 4,
            "Description": 0,
            "Particular": 40,
            "Document due date": 0,
            "Quantity": 0,
            "Unit": 0,
            "Offset": 0
        }

        # # 5.
        # # Start generate the download file we want
        # txt = open('./flexacc_output.txt', 'w', encoding='utf-8')
        # for master_exp_id in ids:
        #     record = http.request.env['hhexpense.hhexpense'].sudo().search([('id', '=', int(master_exp_id))])
        #     for exp_line in record.expense_line:
        #
        #         # Check if record contains remarks
        #         # if we do not have following code, it will display "false" instead of empty
        #         # remarks = ""
        #         if exp_line.expense_line_name:
        #             # employee name + expense date + description
        #             remarks = exp_line.employee_name \
        #                       + " / " + \
        #                       exp_line.expense_line_date\
        #                       + " / " + \
        #                       exp_line.expense_line_name
        #             print("get description: ", remarks)
        #         else:
        #             remarks = ""
        #
        #         # According to requirement, currency and original amount storage is kind of different.
        #         # For non-RMB record (currency is HKD, JPY, USD...),
        #             # store it as HKD currency in file,
        #             # thus, rate should correspondingly change to (HKD --> HKD)
        #             # use calculated value (expense_line_calculate) as original amount to store in file,
        #             # also use calculated value (expense_line_calculate) as calculated amount to store in file.
        #         # For RMB record (currency is RMB...),
        #             # store it as RMB currency in file,
        #             # thus, rate will keep the same (use exchange_rate value)
        #             # use original amount that input by user (expense_line_cost) as original amount to store in file,
        #             # therefore, we need Re-calculate its calculated amount(RMB-->HKD) to store in file.
        #         if exp_line.pay_bank_cash == "Bank":
        #             convert_currency_to_format = "HKD"
        #             original_amount = calculated_amount = exp_line.expense_line_calculate
        #             convert_rate = http.request.env['hhexpense.currency.rate'].\
        #                            search([('currency', '=', "HKD")]).exchange_rate
        #         else:
        #             convert_currency_to_format = "RMB"
        #             original_amount = exp_line.expense_line_cost
        #             convert_rate = http.request.env['hhexpense.currency.rate'].\
        #                            search([('currency', '=', "RMB")]).exchange_rate
        #             calculated_amount = original_amount * convert_rate
        #         format_original_amount = "%0.2f" % original_amount
        #         format_rate = "%0.4f" % convert_rate
        #         format_equv_amount = "%0.2f" % calculated_amount
        #
        #         # Generate FlexAccount file
        #         # First transaction for one record (debit acc; D)
        #         # 1.Voucher type - 2.Voucher reference - 3.Voucher date dd - 4.offset - 5.Voucher date mm - 6.offset -
        #         # 7.Voucher date yy - 8.A/C - 9.Analysis code 1 - 10.Analysis code 2 - 11.Analysis code 3 -
        #         # 12.Analysis code 4 - 13.Analysis code 5 - 14.Currency - 15.Amount - 16.Exchange rate -
        #         # 17.Equv. amount - 18.D/C sign - 19.Document no. - 20.Document type - 21.Document date dd -
        #         # 22.offset - 23.Document date mm - 24.offset - 25.Document date yy - 26.Payment term - 27.Description -
        #         # 28.Particular - 29.Document due date - 30.Quantity - 31.Unit - 32.offset
        #         contents = [
        #             # 1-6
        #             "PC", "", date_d, offset, date_m, date_y_l,
        #             # 7-11
        #             date_y_r, str(exp_line.expense_debit_acc), "", "", analysis_code,
        #             # 12-16
        #             "", "", convert_currency_to_format, str(format_original_amount),
        #             str(format_rate),
        #             # 17-21
        #             str(format_equv_amount), "D", "", "", "",
        #             # 22-27
        #             "", "", "", "", "", "",
        #             # 28-32
        #             remarks, "", "", "", ""
        #                     ]
        #         for i, (content, length) in enumerate( zip(contents, format_dic.values()) ):
        #             # i start from 0, not 1
        #             if i == 1:
        #                 txt.write(content.rjust(length, "0"))
        #             elif i == 14 or i == 15 or i == 16:
        #                 txt.write(content.rjust(length, " "))
        #             else:
        #                 txt.write(content.ljust(length, " "))
        #         # One record has been insert, next record goes to next line
        #         txt.write('\n')
        #
        #         # Second transaction for the same record (debit acc --> credit acc; D --> C)
        #         sec_contents = [
        #             # 1-6
        #             "PC", "", date_d, offset, date_m, date_y_l,
        #             # 7-11
        #             date_y_r, str(exp_line.credit_acc), "", "", "",
        #             # 12-16
        #             "", "", convert_currency_to_format, str(format_original_amount),
        #             str(format_rate),
        #             # 17-21
        #             str(format_equv_amount), "C", "", "", "",
        #             # 22-27
        #             "", "", "", "", "", "",
        #             # 28-32
        #             remarks, "", "", "", ""
        #         ]
        #         for i, (content, length) in enumerate(zip(sec_contents, format_dic.values())):
        #             # i start from 0, not 1
        #             if i == 1:
        #                 txt.write(content.rjust(length, "0"))
        #             elif i == 14 or i == 15 or i == 16:
        #                 txt.write(content.rjust(length, " "))
        #             else:
        #                 txt.write(content.ljust(length, " "))
        #         # One record has been insert, next record goes to next line
        #         txt.write('\n')
        # # Data has been written, operation done, close file
        # txt.close()

        # # 5.
        # # Start generate the download file we want
        # txt = open('./flexacc_output.txt', 'w', encoding='utf-8')
        # for sub_exp_id in ids:
        #     corresponding_record = http.request.env['hhexpense.line'].sudo().search([('id', '=', int(sub_exp_id))])
        #     print("id in the list:", sub_exp_id)
        #     print("sub rec info  :", corresponding_record.id, corresponding_record.expense_line_name)
        #
        #     # Get record's remarks, remarks = employee name + expense date + description
        #     # if we do not have following code, it will display "false" instead of empty
        #     remarks = corresponding_record.employee_name + "/" \
        #               + corresponding_record.expense_line_date + "/" \
        #               + corresponding_record.expense_line_name
        #     print("get description: ", remarks)
        #
        #     # According to requirement and current workflow,
        #     # for all record, whatever currency it is, we will store it as HKD currency in file
        #     # thus, stored(in file) currency rate should correspondingly change to (HKD --> HKD, which is 1.0)
        #     # As a result, we will use calculated value (expense_line_calculate) as original amount to store in file,
        #     # and use calculated value (expense_line_calculate) as calculated amount to store in file.
        #     # original_amount = calculated_amount = record.expense_line_calculate
        #     # convert_rate = http.request.env['hhexpense.currency.rate']. \
        #     #     search([('currency', '=', "HKD")]).exchange_rate
        #     force_convert_currency = "HKD"
        #     convert_rate = 1.0
        #     format_original_amount = format_equv_amount = "%0.2f" % corresponding_record.expense_line_calculate
        #     format_rate = "%0.4f" % convert_rate
        #
        #     # Generate FlexAccount file
        #     # First transaction for one record (debit acc; D)
        #     # 1.Voucher type - 2.Voucher reference - 3.Voucher date dd - 4.offset - 5.Voucher date mm - 6.offset -
        #     # 7.Voucher date yy - 8.A/C - 9.Analysis code 1 - 10.Analysis code 2 - 11.Analysis code 3 -
        #     # 12.Analysis code 4 - 13.Analysis code 5 - 14.Currency - 15.Amount - 16.Exchange rate -
        #     # 17.Equv. amount - 18.D/C sign - 19.Document no. - 20.Document type - 21.Document date dd -
        #     # 22.offset - 23.Document date mm - 24.offset - 25.Document date yy - 26.Payment term - 27.Description -
        #     # 28.Particular - 29.Document due date - 30.Quantity - 31.Unit - 32.offset
        #     contents = [
        #         # 1-6
        #         "PC", "", date_d, offset, date_m, date_y_l,
        #         # 7-11
        #         date_y_r, str(corresponding_record.expense_debit_acc), "", "", analysis_code,
        #         # 12-16
        #         "", "", force_convert_currency, str(format_original_amount),
        #         str(format_rate),
        #         # 17-21
        #         str(format_equv_amount), "D", corresponding_record.expense_num_copy, "", "",
        #         # 22-27
        #         "", "", "", "", "", "",
        #         # 28-32
        #         remarks, "", "", "", ""
        #     ]
        #     for i, (content, length) in enumerate(zip(contents, format_dic.values())):
        #         # i start from 0, not 1
        #         if i == 1:
        #             txt.write(content.rjust(length, "0"))
        #         elif i == 14 or i == 15 or i == 16:
        #             txt.write(content.rjust(length, " "))
        #         else:
        #             txt.write(content.ljust(length, " "))
        #     # One record has been insert, next record goes to next line
        #     txt.write('\n')
        #
        #     # Second transaction for the same record (debit acc --> credit acc; D --> C)
        #     sec_contents = [
        #         # 1-6
        #         "PC", "", date_d, offset, date_m, date_y_l,
        #         # 7-11
        #         date_y_r, str(corresponding_record.credit_acc), "", "", "",
        #         # 12-16
        #         "", "", force_convert_currency, str(format_original_amount),
        #         str(format_rate),
        #         # 17-21
        #         str(format_equv_amount), "C", corresponding_record.expense_num_copy, "", "",
        #         # 22-27
        #         "", "", "", "", "", "",
        #         # 28-32
        #         remarks, "", "", "", ""
        #     ]
        #     for i, (content, length) in enumerate(zip(sec_contents, format_dic.values())):
        #         # i start from 0, not 1
        #         if i == 1:
        #             txt.write(content.rjust(length, "0"))
        #         elif i == 14 or i == 15 or i == 16:
        #             txt.write(content.rjust(length, " "))
        #         else:
        #             txt.write(content.ljust(length, " "))
        #     # One record has been insert, next record goes to next line
        #     txt.write('\n')
        # # Data has been written, operation done, close file
        # txt.close()

        # 5.
        # Start generate the download file we want
        txt = open('./flexacc_output.txt', 'w', encoding='utf-8')
        for sub_exp_id in ids:
            corresponding_record = http.request.env['hhexpense.line'].sudo().search([('id', '=', int(sub_exp_id))])
            print("id in the list:", sub_exp_id)
            print("sub rec info  :", corresponding_record.id, corresponding_record.expense_line_name)

            # Get analysis code
            if corresponding_record.expense_id.team_name:
                # get analysis code
                analysis_code = corresponding_record.expense_id.analysis_code
            else:
                # set analysis code to null
                analysis_code = ""

            # Get record's remarks, remarks = employee name + expense date + description
            # if we do not have following code, it will display "false" instead of empty
            remarks = corresponding_record.employee_name + "/" \
                      + corresponding_record.expense_line_date + "/" \
                      + corresponding_record.expense_line_name
            print("get description: ", remarks)
            # if length over, cut and take 40 char
            if len(remarks) >= 40:
                format_remarks = remarks[:40]
            else:
                format_remarks = remarks


            # According to requirement, currency and original amount storage is kind of different.
            #   For non-RMB record (currency is HKD, JPY, USD...),
            #   store it as HKD currency in file,
            #   thus, rate should correspondingly change to (HKD --> HKD)
            #   use calculated value (expense_line_calculate) as original amount to store in file,
            #   also use calculated value (expense_line_calculate) as calculated amount to store in file.
            # For RMB record (currency is RMB...),
            #   store it as RMB currency in file,
            #   thus, rate will keep the same (use exchange_rate value)
            #   use original amount that input by user (expense_line_cost) as original amount to store in file,
            #   therefore, we need Re-calculate its calculated amount(RMB-->HKD) to store in file.
            if corresponding_record.pay_hkd_rmb == "HKD":
                force_convert_currency = "HKD"
                original_amount = calculated_amount = corresponding_record.expense_line_calculate
                convert_rate = 1.0
            else:
                force_convert_currency = "RMB"
                original_amount = corresponding_record.expense_line_cost
                convert_rate = http.request.env['hhexpense.currency.rate'].\
                    search([('currency', '=', "RMB")]).exchange_rate
                calculated_amount = original_amount * convert_rate
            format_original_amount = "%0.2f" % original_amount
            format_rate = "%0.4f" % convert_rate
            format_equv_amount = "%0.2f" % calculated_amount

            # Generate FlexAccount file
            # First transaction for one record (debit acc; D)
            # 1.Voucher type - 2.Voucher reference - 3.Voucher date dd - 4.offset - 5.Voucher date mm - 6.offset -
            # 7.Voucher date yy - 8.A/C - 9.Analysis code 1 - 10.Analysis code 2 - 11.Analysis code 3 -
            # 12.Analysis code 4 - 13.Analysis code 5 - 14.Currency - 15.Amount - 16.Exchange rate -
            # 17.Equv. amount - 18.D/C sign - 19.Document no. - 20.Document type - 21.Document date dd -
            # 22.offset - 23.Document date mm - 24.offset - 25.Document date yy - 26.Payment term - 27.Description -
            # 28.Particular - 29.Document due date - 30.Quantity - 31.Unit - 32.offset
            contents = [
                # 1-6
                "PC", "", date_d, offset, date_m, date_y_l,
                # 7-11
                date_y_r, str(corresponding_record.expense_debit_acc), "", "", analysis_code,
                # 12-16
                "", "", force_convert_currency, str(format_original_amount),
                str(format_rate),
                # 17-21
                str(format_equv_amount), "D", corresponding_record.expense_num_copy, "", "",
                # 22-27
                "", "", "", "", "", "",
                # 28-32
                format_remarks, "", "", "", ""
                        ]
            for i, (content, length) in enumerate(zip(contents, format_dic.values())):
                # i start from 0, not 1
                if i == 1:
                    txt.write(content.rjust(length, "0"))
                elif i == 14 or i == 15 or i == 16:
                    txt.write(content.rjust(length, " "))
                else:
                    txt.write(content.ljust(length, " "))
            # One record has been insert, next record goes to next line
            txt.write('\n')

            # Second transaction for the same record (debit acc --> credit acc; D --> C)
            sec_contents = [
                # 1-6
                "PC", "", date_d, offset, date_m, date_y_l,
                # 7-11
                date_y_r, str(corresponding_record.credit_acc), "", "", "",
                # 12-16
                "", "", force_convert_currency, str(format_original_amount),
                str(format_rate),
                # 17-21
                str(format_equv_amount), "C", corresponding_record.expense_num_copy, "", "",
                # 22-27
                "", "", "", "", "", "",
                # 28-32
                format_remarks, "", "", "", ""
            ]
            for i, (content, length) in enumerate(zip(sec_contents, format_dic.values())):
                # i start from 0, not 1
                if i == 1:
                    txt.write(content.rjust(length, "0"))
                elif i == 14 or i == 15 or i == 16:
                    txt.write(content.rjust(length, " "))
                else:
                    txt.write(content.ljust(length, " "))
            # One record has been insert, next record goes to next line
            txt.write('\n')
        # Data has been written, operation done, close file
        txt.close()

        # 6.
        # Read the output file for the download
        with open('flexacc_output.txt', 'r') as txt:
            file_content = txt.read()
        os.remove("./flexacc_output.txt")
        # # If you want download file as "self_defined_name".txt, set: filename='download.txt'
        headers = werkzeug.datastructures.Headers()
        if not file_content:
            return request.not_found()
        else:
            # If you want download file as "self_defined_name".txt, set: filename='download.txt'
            filename = 'FlexAcc_' + str(datetime.today().strftime('%Y_%m_%d')) + '.txt'
            headers.set('Content-Disposition', 'attachment', filename=filename)
            return request.make_response(file_content, headers)

    # Making download file fit to HSBC format
    # @http.route('/web/binary/generate_hsbcnet_txt_file', type='http', auth='public', method=['POST'], csrf=False)
    # @http.route('/web/binary/generate_hsbcnet_txt_file', type='http', auth='public')
    # def download_hsbc_txt_file(self, **kwargs):
    #     # Purpose of this function:
    #         # 1.Obtain id data
    #         # 2.Obtain converted_amount data and calculate total amount for selected records
    #         # 3.Obtain anticipated_date data and convert to the format we want (DDMMYY)
    #         # 4.Obtain employee_name data(is unique) and calculate total amount for each employee,
    #         # output a dictionary that contains key-value pair (employee_name - total_amount)
    #         # 5.Create 2 dict to store HSBC header&data format based on HSBC instruction guideline
    #         # 6.Generate other necessary data with the format we want (e.g. a reference string)
    #         # 7.Generate file (write data)
    #         # 8.Download file
    #     print("hi, controller catch the 'Generate HSBCnet txt file' request")
    #
    #     # 1.
    #     # Get selected sub record(that paid by bank)'s id
    #     # based on the file that created in "get_input_anticipated_date" method
    #     # will be used in header
    #     selected_bank_sub_rec_id_list = []
    #     temp_file_get_selected_rec_id = open('./hsbc_intermediate_file_get_selected_rec_id.txt', 'r', encoding='utf-8')
    #     for line in temp_file_get_selected_rec_id:
    #         selected_bank_sub_rec_id_list.append(line.replace('\n', ''))  # E.g. ids = ['1', '2']
    #     temp_file_get_selected_rec_id.close()
    #     os.remove("./hsbc_intermediate_file_get_selected_rec_id.txt")
    #     print("(controller)For selected records, id list: ", selected_bank_sub_rec_id_list)
    #
    #     # 2.
    #     # Calculation: "For selected records, add their converted amount together, becomes a total amount"
    #     # based on the file that created in "get_input_anticipated_date" method
    #     # will be used in header
    #     total_amount_for_selected_rec = 0
    #     temp_file_get_converted_amount = open('./hsbc_intermediate_file_get_converted_amount.txt', 'r', encoding='utf-8')
    #     for line in temp_file_get_converted_amount:
    #         int_line = line.strip('\n')
    #         total_amount_for_selected_rec += float(int_line)
    #     temp_file_get_converted_amount.close()
    #     os.remove("./hsbc_intermediate_file_get_converted_amount.txt")
    #     # make sure data only have 2 decimal
    #     total_amount_for_selected_rec_with_two_decimal = "%0.2f" % round(total_amount_for_selected_rec, 2)
    #     print("(controller)For selected records, total amount: ", total_amount_for_selected_rec)
    #     print("(controller)For selected records, total amount: ", total_amount_for_selected_rec_with_two_decimal)
    #     # In order to fit the format, 456.32 --> 45632, remove point!
    #     # Thus, total amount will be a string that combined with two part: integer_part + decimal_part
    #     total_amount_with_format_for_selected_rec = str(total_amount_for_selected_rec_with_two_decimal)[:-3] + \
    #                                                 str(total_amount_for_selected_rec_with_two_decimal)[-2:]
    #
    #     # 3.
    #     # Get selected sub record's anticipated date (one date for all selected records)
    #     # based on the file that created in "auto_processing" method
    #     # will be used in header
    #     anticipated_upload_date = ''
    #     temp_file_get_anticipated_date = open("./hsbc_intermediate_file_get_selected_rec_anticipated_date.txt", "r", encoding="utf-8")
    #     for line in temp_file_get_anticipated_date:
    #         print("original anticipated upload date:", line)
    #         anticipated_upload_date = line.replace('\n', '')
    #     temp_file_get_anticipated_date.close()
    #     os.remove("./hsbc_intermediate_file_get_selected_rec_anticipated_date.txt")
    #     # anticipated_upload_date value sample: 2018-08-15
    #     print("(controller)For selected records, anticipated upload date: ", anticipated_upload_date)
    #     # remove _ in this string first
    #     date_remove_under = anticipated_upload_date.replace("_", "")
    #     print("remove _ in string:", date_remove_under)
    #     # Convert date to datetime type
    #     convert_date = datetime.strptime(date_remove_under, '%Y-%m-%d')
    #     print("convert date string to date type", convert_date)
    #     # Convert a datetime type date to string with format we want (DDMMYY)
    #     anticipated_upload_date_with_format = datetime.strftime(convert_date, "%d%m%y")
    #     print(anticipated_upload_date_with_format)
    #
    #     # 4.
    #     # Get selected sub record's employee_name
    #     # based on the file that created in "get_input_anticipated_date" method
    #     # Will be used on "Calculate total amount for each employee"
    #     temp_file_get_rec_employee_name = open('./hsbc_intermediate_file_get_rec_employee_name.txt', 'r', encoding='utf-8')
    #     # Use a list to store all different employee name, why not use "set"? Ans: not ez to access element
    #     employee_name_list = []
    #     for line in temp_file_get_rec_employee_name:
    #         pure_string = line.strip('\n')
    #         # Make sure every element in employee_name_list is unique
    #         if pure_string not in employee_name_list:
    #             print("Find new employee name, add!")
    #             employee_name_list.append(pure_string)
    #         else:
    #             print("This employee name already exist in the list, ignore!")
    #     temp_file_get_rec_employee_name.close()
    #     os.remove("./hsbc_intermediate_file_get_rec_employee_name.txt")
    #     print("(controller)For selected records, employee name list: ", employee_name_list)
    #     # Calculate total amount for each employee
    #     # Compare to all record in hhexpense_line model, if name is the same, add corresponding amount and calculate it.
    #     # First, we need create a dic to store key-value pair (employee_name - total_amount),
    #     # we use employee name (data comes from employee_name_list) as key since they are unique
    #     employee_and_own_total_amount_dict = {}
    #     for each_employee in employee_name_list:
    #         print("(controller)Start calculate this employee's total amount")
    #         # Then, we need a variable to store calculated amount
    #         total_amount_for_this_employee = 0
    #         # For each sub-record in hhexpense_line, check if it is belongs to
    #         # current test-looping-employee (with other 2 conditions). If yes, add its amount
    #         get_all_sub_rec = http.request.env['hhexpense.line'].sudo().search([])
    #         for sub_rec in get_all_sub_rec:
    #             # Check if this sub record belongs to this employee
    #             # and check if this sub record is one of the selected record in this time
    #             # It will avoid calculating data if it is used before)
    #             if sub_rec.expense_id.employee_name == each_employee \
    #                and sub_rec.anticipated_date == anticipated_upload_date:
    #                     total_amount_for_this_employee = total_amount_for_this_employee + sub_rec.expense_line_calculate
    #         # Current test-looping-employee's calculation done, save into dict as key - pair,
    #         # but before saving, make sure it has 2 decimal digits!
    #         print("make sure 2 decimal: ", "%0.2f" % total_amount_for_this_employee)
    #         employee_and_own_total_amount_dict[each_employee] = "%0.2f" % total_amount_for_this_employee
    #     print("(controller)For selected records, all different 'employee - total_amount' key-value pair are:",
    #           employee_and_own_total_amount_dict)
    #
    #     # 5.
    #     # Create a dictionary to store HSBC header format based on HSBC instruction guideline
    #     hsbc_header_format_dic = {
    #         "Auto plan Code": 1,  # "F"
    #         "First Party Current Account Number": 12,  # Account No. that company used to pay expense
    #         "Payment Code": 3,  # Waiting for Accounting input/decide
    #         "First Party Reference": 12,  # e.g."250818"(dynamic) + "EmpExp"
    #         "Value Date": 6,  # Accountant(shirley) input date --- anticipated date
    #         "Input Medium": 1,  # "K"
    #         "File Name": 8,  # "********", 8 digits
    #         "Total No of Instruction": 5,  # How many record you have in this file
    #         "Total Amount of Instruction": 10,  # The total amount for this file
    #         "Overflow Total No of Instruction": 7,  # Empty, fill with space
    #         "Overflow Total Amount of Instruction": 12,  # Empty, fill with space
    #         "FILLER": 2,  # Empty, fill with space
    #         "Instruction Source": 1  # "1"
    #     }
    #     # Create a dictionary to store HSBC data format based on HSBC instruction guideline
    #     hsbc_data_format_dic = {
    #         "FILLER": 1,  # Empty, fill with space
    #         "Second Party Identifier": 12,  # "Reimburse"
    #         "Second Party Bank Account Name": 20,  # employee name
    #         "Second Party Account": 15,  # employee Account's bank number(3) + branch number(3) + Account No.(9)
    #         # "Second Party Bank Number": 3,  # employee Account's bank number
    #         # "Second Party Branch Number": 3,  # employee Account's branch number
    #         # "Second Party Account": 9,  # employee Account No.
    #         "Amount": 10,  # total amount for one employee
    #         "Filler": 4,  # Empty, fill with space
    #         # "Second Party Identifier Continuation": 6,
    #         # "Second Party Reference": 12
    #     }
    #
    #     # 6.
    #     # Generate "First Party Reference", will be used in file header
    #     # year = str(datetime.now().year)[-2:]
    #     d_m_and_y = str(date.today().strftime('%d%m%y'))
    #     reference = d_m_and_y + "EmpExp"  # Example:"030219EmpExp" format:"ddmmyy + EmpExp"
    #     print("reference for download file: ", reference)
    #     # Obtain "company acc info", will be used in file header
    #     # comp_list = http.request.env['res_company'].search([])
    #     # comp_acc = ""
    #     # for comp in comp_list:
    #     #     if comp.name == 'HungHingPrinting':
    #     #         comp_acc = comp.account_no
    #     #     else:
    #     #         pass
    #     # why this code not working? IndexError: string index out of range
    #     # com_acc = self.env['res.company'].search(['id', '=', '3']).account_no
    #     # com_acc = self.env['res.company'].sudo().search(['name', '=', 'HungHingPrinting']).account_no
    #     company_acc_for_hsbc = "600331102001"
    #
    #     # 7.
    #     # Start generate the download file we want
    #     # if you add --- newline='\n' --- here (not add when reading file(line:485))
    #     # system will still interpret newline as unix style (LF)
    #     txt = open('./hsbc_output.txt', 'w', encoding='utf-8')
    #     # Generate file's header
    #     hsbc_header_contents = [
    #         # 1-6
    #         "F", company_acc_for_hsbc, "O03", reference, anticipated_upload_date_with_format, "K",
    #         # 7-11
    #         "********", str(len(employee_name_list)), total_amount_with_format_for_selected_rec, "", "",
    #         # 12-13
    #         "", "1"
    #     ]
    #     # Fill out empty space with format
    #     for i, (content, length) in enumerate(zip(hsbc_header_contents, hsbc_header_format_dic.values())):
    #         # i is index not position, start with 0
    #         if i == 1 or i == 7 or i == 8:
    #             txt.write(content.rjust(length, "0"))
    #         else:
    #             txt.write(content.ljust(length, " "))
    #     # File header has been insert and settled
    #     txt.write('\n')
    #     # Generate file's data contents line by line
    #     for key in employee_and_own_total_amount_dict.keys():
    #
    #         # Obtain employee account No.
    #         # Get all info
    #         emp_info = http.request.env['hr.employee'].sudo().search([])
    #         # Use a variable to store acc
    #         current_emp_acc = ""
    #         for emp in emp_info:
    #             if emp.name == key:
    #                 current_emp_acc = emp.bank_account_id.acc_number
    #                 print("this employee: " + key + "'s Acc No. is: " + current_emp_acc)
    #
    #                 # For each record, its amount should be with correct format --- remove point
    #                 total_amount_for_this_employee_with_format = str(employee_and_own_total_amount_dict[key])[:-3] + \
    #                                                              str(employee_and_own_total_amount_dict[key])[-2:]
    #
    #                 # hsbc_data_contents = [
    #                 #     # 1-6
    #                 #     # "CCC", "DDD", "AAAAAAAA" can be together, since these 3 data are continuously data
    #                 #     "", "Reimburse", key, "CCC", "DDD", "AAAAAAAA",
    #                 #     # 7-8
    #                 #     total_amount_for_this_employee_with_format, ""
    #                 # ]
    #                 hsbc_data_contents = [
    #                     # 1-4
    #                     "", "Reimburse", key, current_emp_acc,
    #                     # 5-6
    #                     total_amount_for_this_employee_with_format, ""
    #                 ]
    #                 # Fill out empty space with format
    #                 for i, (content, length) in enumerate(zip(hsbc_data_contents, hsbc_data_format_dic.values())):
    #                     if i == 4:
    #                         txt.write(content.rjust(length, "0"))
    #                     else:
    #                         txt.write(content.ljust(length, " "))
    #                 # One record has been insert, next record goes to next line
    #                 txt.write('\n')
    #                 # All data has been written (header + data), operation done, close file
    #     txt.close()
    #
    #     # 8.
    #     # Read the file for the download action
    #     # You need add --- newline='\n' --- here so that system will interpret newline as windows style (CRLF),
    #     # not add when writing file(line:399) is fine,
    #     with open('hsbc_output.txt', 'r', newline='\n') as txt:
    #         file_content = txt.read()
    #     # os.remove("./hsbc_output.txt")
    #     # If you want download file as "self_defined_name".txt, set: filename='download.txt'
    #
    #
    #     headers = werkzeug.datastructures.Headers()
    #     if not file_content:
    #         return request.not_found()
    #         # 'type': 'ir.actions.client',
    #         # 'tag': 'reload',
    #     else:
    #         # If you want download file as "self_defined_name".txt, set: filename='download.txt'
    #         headers.set('Content-Disposition', 'attachment', filename='HSBC_download.txt')
    #         return request.make_response(file_content, headers)
    #         # 'type': 'ir.actions.client',
    #         # 'tag': 'reload',

    @http.route('/web/binary/download_reports', type='http', auth='public', method=['GET'], csrf=False)
                # method=['POST'], csrf=False)
    def make_http_response(self, **kwargs):
        """
        This function requires the werkzeug library to input the excel file and make an http response to the user.
        The batch number is passed by the url, eg. ?key=value&key1=value1  .

        io.BytesIO() is a function to write data to memory and in this case the zipfile is written in memory and file
        bytes string are stored in zip.

        file.seek(0) is to move the pointer to the start of the data bytes and allows the .read() to read bytes starting
        there
        """
        import zipfile
        import io
        import os

        batch_no = kwargs['batch_no']
        has_file = kwargs['has_file']
        mem_file = io.BytesIO()
        files = []

        if 'R' in has_file:
            files.append('RMB_%s' % batch_no)
        if 'H' in has_file:
            files.append('HKD_%s' % batch_no)

        with zipfile.ZipFile(mem_file, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for name in files:
                zf.write('./%s.txt' % name)
                zf.write('./%s.xlsx' % name)
                os.remove('./%s.txt' % name)
                os.remove('./%s.xlsx' % name)

        mem_file.seek(0)
        data = mem_file.read()

        file = '%s.zip' % batch_no
        headers = werkzeug.datastructures.Headers()

        headers.set('Content-Disposition', 'attachment', filename=file)
        return request.make_response(data, headers)
