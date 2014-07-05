# Copyright (C) 2014 - Frans0

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QKeySequence
from PyQt5.QtWidgets import (QApplication, QMessageBox, QShortcut, QTableWidgetItem, QCheckBox, QToolBar, QLabel,
                             QVBoxLayout, QTableWidget, QDialog, QPlainTextEdit, QPushButton, QSizePolicy, QWidget,
                             QDialogButtonBox)

SURROUNDING_TEXT_RANGE = 20  # The surrounding text contains 20 chars before the mail address, and 20 after


class MailAddress:
    last_id = 0

    def __init__(self, mail_address, is_mail_link=False, tag_text='', surround_text='',
                 start_pos=0, end_pos=0):
        self.id = MailAddress.last_id
        MailAddress.last_id += 1

        self.mail_address_text = mail_address
        self.is_mail_link = is_mail_link
        self.tag_text = tag_text
        self.surrounding_text = surround_text
        self.start_pos = start_pos
        self.end_pos = end_pos


class Window(QWidget):
    def __init__(self):
        super(Window, self).__init__()
        self.plain_text_edit = QPlainTextEdit()  # Create a plain text edit widget
        self.populate_ui()
        self.setWindowTitle("Convert plain text mail addresses to links")
        self.resize(1000, 600)

    # Puts all the widgets in the GUI and connects the signals with slots
    def populate_ui(self):
        self.plain_text_edit.setFont(QFont("Courier", 9))  # Makes HTML more readable

        # At the moment there is only one button, but the QToolBar makes it
        # easier to add more buttons, and it doesn't make the button stretch
        # over the whole width
        button_bar = QToolBar()
        btn_convert_to_links = QPushButton("Convert to links (Ctrl+Q)")  # Button to find all the email addresses
        button_bar.addWidget(btn_convert_to_links)

        # Fill the layout with the widgets that we have created
        main_layout = QVBoxLayout()
        main_layout.addWidget(QLabel("Enter HTML code containing mail addresses:"))
        main_layout.addWidget(self.plain_text_edit)
        main_layout.addWidget(button_bar)

        # Connect signals to slots
        btn_convert_to_links.clicked.connect(self.find_email_links)  # Connect the button
        QShortcut(QKeySequence("Ctrl+Q"), self, self.find_email_links)  # And create a shortcut for it

        self.setLayout(main_layout)

    # Finds the email addresses in the text, and if there is at least 1 found,
    # it opens a dialog with these addresses listed
    def find_email_links(self):
        # A mail address is found if there is a string of legal characters
        # (a-z, A-Z, 0-9, -, _, ., @, +, ~), between non legal characters. This
        # causes the script not to find email addresses if they are located at
        # the end of the file. This is why there is added a space to the end.
        text = self.plain_text_edit.toPlainText() + ' '  # Get the text from the QPlainTextEdit

        mail_addresses = []
        is_in_mail_address = False
        last_non_legal_character = -1  # First place for an email address to start
        last_opening_bracket = 0  # Last opening bracket found at this location
        # Must find a '>' to have tag_text set to a value
        tag_text = ""  # Text in the last tag (<  >)
        is_in_tag = False  # Don't check for mail addresses within tags

        # Check for all characters in the text, whether they are inside a tag, and if not, whether
        # they form part of an email address (if there is a '@' in the string). If they form part
        # of an email address the punctuation marks ('.''s) are trimmed from it
        for i in range(len(text)):
            if not is_in_tag:
                if self.is_character_legal(text[i]):  # If the character is legal in email addresses
                    if text[i] == '@':  # If there is a @ somewhere in the string
                        is_in_mail_address = True  # it is considered an email address
                else:
                    if is_in_mail_address:  # The end of en email address has been found
                        is_in_mail_address = False
                        mail_address = text[last_non_legal_character + 1: i]  # mail_address is set

                        if mail_address[0] != '@' and mail_address[-1] != '@':  # Don't consider mail addresses starting
                            # or ending with @
                            mail_is_link = False  # Innocent until proven guilty

                            # Instead of "href" we could use "mailto", but now we consider all links
                            if "href" in tag_text.lower():  # If the last tag contains a link
                                #  address
                                mail_is_link = True  # proven guilty

                            # Collect the information needed to change the address to a link
                            mail_address = self.remove_trailing_dots(mail_address)

                            start_pos = last_non_legal_character + 1  # After the last character that is not
                            # in the mail address, the mail address
                            # starts
                            end_pos = start_pos + len(mail_address)  # to fix for punctuation trimmed from
                            # the end

                            # The surrounding text starts either at 0, or (by default) 20 positions before the mail
                            # address, depends which one comes later
                            start_surround_text = max(0, start_pos - SURROUNDING_TEXT_RANGE)

                            # The surrounding text ends either at the end of the whole text, or (by default) 20
                            # positions after the email address
                            end_surround_text = min(end_pos + SURROUNDING_TEXT_RANGE, len(text))

                            surround_text = text[start_surround_text:end_surround_text]

                            # Set the properties of the mail address
                            mail_address_item = MailAddress(mail_address, mail_is_link, tag_text,
                                                            surround_text, start_pos, end_pos)

                            # And add it to the list
                            mail_addresses.append(mail_address_item)

                    last_non_legal_character = i
                    if text[i] == '<':
                        last_opening_bracket = i
                        is_in_tag = True
            else:
                if text[i] == '>':
                    tag_text = text[last_opening_bracket:i + 1]
                    is_in_tag = False
                    last_non_legal_character = i

        # if there are no email addresses found, there is no need for the MailTable dialog
        if len(mail_addresses) == 0:
            QMessageBox.information(self, "No addresses found",
                                    "The script couldn't recognize email addresses in the text.")

        else:
            # If there are email addresses found
            m = MailTable(mail_addresses, self)
            m.exec_()

            # when the dialog is closed
            new_text = ""
            old_text = self.plain_text_edit.toPlainText()
            last_pos = 0  # Last position in old text

            mail_addresses_to_change = m.get_mail_addresses_to_change()

            for mail_address in mail_addresses_to_change:
                mailaddr_text = mail_address.mail_address_text
                start_pos = mail_address.start_pos
                end_pos = mail_address.end_pos

                new_text = new_text + old_text[last_pos: start_pos] + "<a href=\"mailto:" + mailaddr_text + "\">" + \
                           old_text[start_pos:end_pos] + "</a>"
                last_pos = end_pos
            # and at the last part of the text
            new_text = new_text + old_text[last_pos: -1]

            self.plain_text_edit.setPlainText(new_text)

    @staticmethod
    def is_character_legal(a):
        if a.isalnum():
            return True
        if a in ['-', '_', '.', '@', '+', '~']:
            return True
        return False

    @staticmethod
    def remove_trailing_dots(text):
        while text.endswith('.'):
            text = text[0:-1]
        return text


class MailTable(QDialog):
    def __init__(self, mail_addresses, parent=None):
        super(MailTable, self).__init__(parent)
        layout = QVBoxLayout()
        self.table = QTableWidget(len(mail_addresses), 4)
        self.mail_addresses = mail_addresses

        table = self.table
        table.setFont(QFont("Sans", 8))

        header_labels = ['Should be converted?', 'Is link?', 'Preceding tag', 'Surrounded text']
        table.setHorizontalHeaderLabels(header_labels)

        table.verticalHeader().setDefaultSectionSize(20)

        row_nr = 0
        for mail_address in mail_addresses:
            mailaddr_item = QTableWidgetItem(mail_address.mail_address_text)
            mailaddr_item.setCheckState(Qt.Unchecked)

            is_mail_link_item = QTableWidgetItem(str(mail_address.is_mail_link))
            is_mail_link_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # Make the cell not editable
            if mail_address.is_mail_link:
                is_mail_link_item.setBackground(Qt.green)
            else:
                is_mail_link_item.setBackground(Qt.red)

            tag_text_item = QTableWidgetItem(mail_address.tag_text)
            tag_text_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

            surrounding_text_item = QTableWidgetItem(mail_address.surrounding_text)
            surrounding_text_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            surrounding_text_item.setFont(QFont("Courier", 10))

            table.setItem(row_nr, 0, mailaddr_item)
            table.setItem(row_nr, 1, is_mail_link_item)
            table.setItem(row_nr, 2, tag_text_item)
            table.setItem(row_nr, 3, surrounding_text_item)

            row_nr += 1

        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)

        btn_select_non_links = QPushButton("Select all non-links")
        btn_select_all = QPushButton("Select all")
        btn_select_none = QPushButton("Clear selection")
        btn_selection_invert = QPushButton("Invert selection")

        button_box = QDialogButtonBox()
        button_box.addButton(btn_select_non_links, QDialogButtonBox.ActionRole)
        button_box.addButton(btn_select_all, QDialogButtonBox.ActionRole)
        button_box.addButton(btn_select_none, QDialogButtonBox.ActionRole)
        button_box.addButton(btn_selection_invert, QDialogButtonBox.ActionRole)

        button_box.addButton("Ok", QDialogButtonBox.AcceptRole)

        layout.addWidget(QLabel("Which addresses should be converted?"))
        layout.addWidget(table)
        layout.addWidget(button_box)

        button_box.accepted.connect(self.accept)
        btn_select_all.clicked.connect(self.select_all)
        btn_select_non_links.clicked.connect(self.select_all_non_links)
        btn_select_none.clicked.connect(self.select_none)
        btn_selection_invert.clicked.connect(self.selection_invert)

        # Default to select that all addresses that are no links
        self.select_all_non_links()

        self.setWindowTitle(str(len(mail_addresses)) + " email addresses found")
        self.setLayout(layout)
        self.resize(1000, 500)

    def select_all(self):
        table = self.table
        for i in range(table.rowCount()):
            table.item(i, 0).setCheckState(Qt.Checked)

    def select_all_non_links(self):
        table = self.table
        for i in range(table.rowCount()):
            is_mail_link = self.mail_addresses[i].is_mail_link

            if not is_mail_link:
                table_item = table.item(i, 0)
                table_item.setCheckState(Qt.Checked)

    def select_none(self):
        table = self.table
        for i in range(table.rowCount()):
            table.item(i, 0).setCheckState(Qt.Unchecked)

    def selection_invert(self):
        table = self.table
        for i in range(table.rowCount()):
            ti = table.item(i, 0)
            c = ti.checkState()

            if c == Qt.Unchecked:
                ti.setCheckState(Qt.Checked)
            else:
                ti.setCheckState(Qt.Unchecked)

    def get_mail_addresses_to_change(self):
        table = self.table
        mail_addresses_to_change = []
        for i in range(table.rowCount()):
            if table.item(i, 0).checkState() == Qt.Checked:
                mail_address = self.mail_addresses[i]
                mail_address.mail_address_text = table.item(i, 0).text()

                mail_addresses_to_change.append(mail_address)

        return mail_addresses_to_change


import sys

qApp = QApplication(sys.argv)
mainWin = Window()
mainWin.show()
sys.exit(qApp.exec_())
