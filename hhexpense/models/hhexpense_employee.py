# -*- coding: utf-8 -*-
from odoo import models, api
import psycopg2
import datetime


class HHExpenseEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def create(self, vals):
        print('you are in hhexpense module to create an employee')
        # In the vals you will have the work email and all other details
        # Here we limit user must login odoo system with their HungHing Email to make themselves to be unique
        user_rec = self.env['res.users'].search([('login', '=', vals['work_email'])], limit=1)
        vals['user_id'] = user_rec.id
        print('user id:', user_rec.id)
        res = super(HHExpenseEmployee, self).create(vals)
        print('resource_id:', res.resource_id)
        return res

    def get_employee_info(self):
        # for this part, we need to add info for res_company called HungHingPrinting
        # and we need to config the outgoing email server firstly
        connect_employee_db = psycopg2.connect(host="172.17.10.198", database="HungHingEmployee", user="odooNew",
                                               password="odoo")
        print("database connected")
        employee_db_cur = connect_employee_db.cursor()

        # connect HH hr database and get employee info
        employee_db_cur.execute(
            """SELECT name, department, email, account_number, bank FROM hunghing_employee_info """)
        employees = employee_db_cur.fetchall()
        # combine bank and bank_acc
        employees_list = []
        for employee in employees:
            bank_acc = str(employee[4] + employee[3])
            list_employee = list(employee)
            list_employee.pop(4)
            list_employee.pop(3)
            list_employee.append(bank_acc)
            employee = tuple(list_employee)
            employees_list.append(employee)
        # for emoloyee in employees_list:
        #     print('employee_list:', emoloyee, '\n')

        # 1>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>first handle people who leave the company
        # get new data and old data from employee and department
        after_email_list = []
        before_email_list = []
        # get company_id first
        odoo_cr = self.env.cr
        odoo_cr.execute("""SELECT id FROM res_company where name='Hung Hing Offset Printing Co., Ltd' """)
        company_id = odoo_cr.fetchall()

        # new data
        for new_employee in employees:
            after_email_list.append(new_employee[2])

        # old data
        # odoo_cr.execute("""delete FROM res_users where active=false """)
        odoo_cr.execute("""SELECT login FROM res_users where id!=1 and active=true """)
        before_employee_info = odoo_cr.fetchall()
        for before_employee in before_employee_info:
            before_email_list.append(before_employee[0])

        # check if there are employees already leave the company
        old_people = list(set(before_email_list) - set(after_email_list))
        print('old_people:', old_people)
        print('--------------------------------  check resigned employee  --------------------------------------------')
        if len(old_people) != 0:
            for people in old_people:
                # delete bank_acc
                odoo_cr.execute("""SELECT bank_account_id FROM hr_employee where work_email= %s""", (people, ))
                delete_bank_id = odoo_cr.fetchall()
                odoo_cr.execute("""DELETE FROM res_partner_bank where id=%s""", (delete_bank_id[0], ))
                # deactive ole people in resource_resource, res_user, res_partner, hr_employee
                odoo_cr.execute("""SELECT resource_id FROM hr_employee where work_email= %s""", (people,))
                delete_resource_id = odoo_cr.fetchall()
                odoo_cr.execute("""update res_users set active=false where login=%s""", (people,))
                odoo_cr.execute("""update res_partner set active=false where email=%s""", (people,))
                odoo_cr.execute("""update hr_employee set active=false where work_email=%s""", (people,))
                odoo_cr.execute("""update resource_resource set active=false where id=%s""", (delete_resource_id[0],))
                print('     >>>already deactive old hr_employee', people)
            print('>>>data clear completed\n')
        else:
            print('>>>no resigned people today-----', datetime.datetime.now(), '\n')

        # check if there are new employees coming into company
        new_people = list(set(after_email_list) - set(before_email_list))
        print('new_people:', new_people)
        print('--------------------------------  check new employee  -------------------------------------------------')
        if len(new_people) != 0:
            # get user access control info
            odoo_cr.execute("""SELECT id FROM res_groups where name='Employee'""")
            employee_access_control = odoo_cr.fetchall()
            # print(employee_access_control[0][0])
            odoo_cr.execute(
                """SELECT id FROM res_groups where name='Technical Features'""")
            technical_access_control = odoo_cr.fetchall()
            # print(technical_access_control)
            odoo_cr.execute(
                """SELECT id FROM res_groups where name='General user'""")
            hhexpense_acc_control = odoo_cr.fetchall()
            # print(hhexpense_acc_control)
            # odoo_cr.execute(
            #     """SELECT id FROM res_groups where name='Public'""")
            # public_control = odoo_cr.fetchall()
            # # print(hhexpense_acc_control)

            for people in new_people:
                # create new users for each new_people
                # 1>>>>>>>>>>>>>>>>>>>>>>>>   find complete data of each new_people, for now, new_people only has email
                # check if there are any previous login email same with the current one
                odoo_cr.execute("""select login from res_users""")
                previous_login_email = odoo_cr.fetchall()
                people_list = [people]
                people_check = tuple(people_list)
                # get complete imfo according to email info
                new_people_info = [item for item in employees_list if item[2] == people][0]
                # write log if there are duplicated info and jump this people's creation
                if people_check in previous_login_email:
                    # print('*******what what what!!!!!! duplicated data!!!! current new employee email', people_check,
                    #       ' is same as previous one******')
                    print(' >>>*******duplicated data!!!!, jump creation process of ', new_people_info[0])
                    with open("./hhemployee_log/newDuplicatedEmployee.txt", "a") as text_file:
                        print(f"--{datetime.datetime.now()}-- new employee ** {new_people_info[0]} ** "
                              f"coming with duplicated email ** {people_check} "
                              f"**, please have a double check \n", file=text_file)
                else:
                    print(' >>>start update info for ', new_people_info[0])

                    # print('new_people_info:', new_people_info)
                    # insert each people into res_users
                    vals = {'active': True, 'company_ids': [[6, False, [company_id[0][0]]]], 'company_id': company_id[0][0],
                            'lang': 'en_US', 'tz': 'Asia/Hong_Kong',
                            'notification_type': 'email', 'name': new_people_info[0], 'email': new_people_info[2],
                            'login': new_people_info[2],
                            'groups_id': [(6, 0, [employee_access_control[0][0], technical_access_control[0][0],
                                                  hhexpense_acc_control[0][0]])]}
                    # 2>>>>>>>>>>>>>>>>>>>>>>>>   create res_users
                    self.env['res.users'].create(vals)
                    print('     >>> res_user', new_people_info[0], 'create completed')

                    # 3>>>>>>>>>>>>>>>>>>>>   add bank acc for new people and append bank_acc_id to new_people_info
                    append_bank_employee_lists = []
                    odoo_cr.execute('INSERT INTO res_partner_bank (acc_number, sanitized_acc_number) '
                                    'VALUES (%s, %s) returning id;', (new_people_info[3], new_people_info[3]))
                    bank_account_id = odoo_cr.fetchall()
                    new_people_info = new_people_info + bank_account_id[0]
                    append_bank_employee_lists.append(new_people_info)
                    # employees_list = append_bank_employee_lists
                    print('         >>> bank id inserted to employee list', append_bank_employee_lists)

                    # 4>>>>>>>>>>>>>>>>>>>>>>>>   check department info of new people
                    department_list=[]
                    odoo_cr.execute("""SELECT name FROM hr_department """)
                    current_departments = odoo_cr.fetchall()
                    for department in current_departments:
                        department_list.append(department[0])
                    # print('department_list:', department_list)

                    # if department is already exist, check its department id
                    if new_people_info[1] in department_list:
                        print('         >>> department already exist')
                        odoo_cr.execute("""SELECT id FROM hr_department where name=%s;""", (new_people_info[1], ))
                        department_id = odoo_cr.fetchall()
                        # print(department_id)
                    # else create a new department and get corresponding id
                    else:
                        print('         >>> wow!!!! new department')
                        # insert department into odoo and update corresponding id
                        odoo_cr.execute('INSERT INTO hr_department (name, complete_name, active, company_id) '
                                        'VALUES (%s, %s, true ,1) returning id;', (new_people_info[1], new_people_info[1]))
                        department_id = odoo_cr.fetchall()
                    new_people_info = new_people_info + department_id[0]
                    # print('with department id new people info:', new_people_info)

                    # 5>>>>>>>>>>>>>>>>>>>>>>>>   create employee info for new people

                    odoo_cr.execute("""SELECT id FROM res_users where login = %s""", (new_people_info[2],))
                    user_id = odoo_cr.fetchall()

                    odoo_cr.execute("""SELECT id FROM res_partner where name='HungHingPrinting' """)
                    address_id = odoo_cr.fetchall()

                    # insert resource info in odoo
                    odoo_cr.execute("""
                                            INSERT INTO resource_resource (name, active, resource_type, calendar_id, company_id,
                                            user_id, time_efficiency)
                                            VALUES (%s, true, %s, 1, %s, %s, 100) returning id;""",
                                    (new_people_info[0], 'user', company_id[0], user_id[0]))
                    resource_id = odoo_cr.fetchall()
                    odoo_cr.execute('INSERT INTO hr_employee (name, active, address_home_id, work_email, resource_id, '
                                    'bank_account_id, department_id, address_id) '
                                    'VALUES (%s, true, null, %s, %s, %s, %s, %s) returning id;',
                                    (new_people_info[0], new_people_info[2], resource_id[0], new_people_info[4], new_people_info[5], address_id[0]))
                    print('     >>>hr_employee', new_people_info[0], ' create completed')
            print('>>>update new people info completed-----\n')

        else:
            print('>>>no new people today-----', datetime.datetime.now(), '\n')

        # >>>>>>>>>>>>>>>>>>>>>>>>   now we start to handle changed info for existing employee
        # print('new_people:', new_people)
        print('employees_list length:', len(employees_list))
        odoo_cr.execute("""SELECT name, department_id,work_email, bank_account_id FROM hr_employee where id!=1 and active=true""")
        yesterday_info = odoo_cr.fetchall()
        print('yesterday_info length:', len(yesterday_info))
        for people in new_people:
            for employee in employees_list:
                if people in list(employee):
                    # drop new people from todays employee list to check changed info
                    employees_list.remove(employee)
            for y_employee in yesterday_info:
                if people in list(y_employee):
                    # drop new people from yesterday employee list to check changed info
                    yesterday_info.remove(y_employee)
        print('exist employees in employees_list', len(employees_list), 'drop inserted new people from today table')
        print('exist employees in yesterday_info', len(yesterday_info), 'drop inserted new people and maybe duplicated '
                                                                        'people from current employee table')
        print('--------------------------------  check info change for existing employee  ----------------------------')
        # get mapping table of department
        odoo_cr.execute(
            """SELECT name, id FROM hr_department where active=true""")
        department_result = odoo_cr.fetchall()
        department_mapping = dict(department_result)
        # print('department_result:', department_mapping)

        # get mapping table of bank_acc
        odoo_cr.execute(
            """SELECT acc_number, id FROM res_partner_bank""")
        bank_result = odoo_cr.fetchall()
        bank_mapping = dict(bank_result)
        # print('bank_result:', bank_mapping)

        for new_info in employees_list:
            for old_info in yesterday_info:
                if new_info[2] == old_info[2]:
                    # keep record for number of changes
                    counter = 0
                    # check if any change of department
                    # check if it is a new department
                    if new_info[1] in department_mapping.keys():
                        if department_mapping[new_info[1]] == old_info[1]:
                            new_department_id = old_info[1]
                            pass
                        else:
                            new_department_id = department_mapping[new_info[1]]
                            counter = counter+1
                            print(f'        >>> change {new_info[0]} to {new_info[1]} department')
                    else:
                        print(f'        >>> wow!!!! {new_info[0]} changes to a new department')
                        # insert department into odoo and update corresponding id
                        odoo_cr.execute('INSERT INTO hr_department (name, complete_name, active, company_id) '
                                        'VALUES (%s, %s, true ,1) returning id;',
                                        (new_info[1], new_info[1]))
                        new_department = odoo_cr.fetchall()
                        new_department_id = new_department[0][0]
                        counter = counter + 1

                    # check if any change of bank_acc
                    if new_info[3] in bank_mapping.keys():
                        new_bank_id = old_info[3]
                    else:
                        odoo_cr.execute("""DELETE FROM res_partner_bank where id=%s""", (old_info[3],))
                        odoo_cr.execute('INSERT INTO res_partner_bank (acc_number, sanitized_acc_number) '
                                        'VALUES (%s, %s) returning id;', (new_info[3], new_info[3]))
                        new_bank = odoo_cr.fetchall()
                        new_bank_id = new_bank[0][0]
                        counter = counter + 1
                        print(f'        >>> change {new_info[0]} bank_acc to{new_info[3]}')

                    # if there is any change, update hr_employee info
                    if counter > 0:
                        odoo_cr.execute(""" update hr_employee set department_id = %s, bank_account_id = %s
                                            where work_email = %s;""", (new_department_id, new_bank_id, new_info[2]))
                        print('    >>>info for employee ', new_info[0], 'has been updated')
                    else:
                        pass
                else:
                    pass
        print('>>>changed info check completed  \n')

        # update email approving manager mapping table
        print('--------------------------------  update email approving manager mapping table -------------------------')
        self.env['hhexpense.approving.manager'].update_approving_manager_list()
        self.env['hhexpense.china.bank.acc'].update_china_bank_acc_list()

        # self.env['hhexpense.reviewing.accountant'].update_reviewing_accountant_list()
        # self.env['hhexpense.verifying.accountant'].update_verifying_accountant_list()
