from unittest import mock

from flask import g
from werkzeug.exceptions import NotFound

from mod_auth.models import Role
from mod_customized.models import CustomizedTest
from mod_regression.models import (Category, InputType, OutputType,
                                   RegressionTest)
from mod_sample.models import Sample
from mod_test.models import Test
from tests.base import BaseTestCase


class TestControllers(BaseTestCase):
    def test_root(self):
        response = self.app.test_client().get('/regression/')
        self.assertEqual(response.status_code, 200)
        self.assert_template_used('regression/index.html')

    def test_specific_regression_test_loads(self):
        response = self.app.test_client().get('/regression/test/1/view')
        self.assertEqual(response.status_code, 200)
        self.assert_template_used('regression/test_view.html')
        regression_test = RegressionTest.query.filter(RegressionTest.id == 1).first()
        self.assertIn(regression_test.command, str(response.data))

    def test_regression_test_status_toggle(self):
        self.create_user_with_role(self.user.name, self.user.email, self.user.password, Role.admin)

        with self.app.test_client() as c:
            c.post('/account/login', data=self.create_login_form_data(self.user.email, self.user.password))

            regression_test = RegressionTest.query.filter(RegressionTest.id == 1).first()
            response = c.get('/regression/test/1/toggle')
            self.assertEqual(response.status_code, 200)
            self.assertEqual('success', response.json['status'])
            if regression_test.active == 1:
                self.assertEqual('False', response.json['active'])
            else:
                self.assertEqual('True', response.json['active'])

    @mock.patch('mod_regression.controllers.RegressionTestOutput')
    def test_download_result_file_not_found(self, mock_regression_output):
        """
        Test that non-existent result file gives 404.
        """
        from mod_regression.controllers import test_result_file
        mock_regression_output.query.filter.return_value.first.return_value = None

        with self.assertRaises(NotFound):
            test_result_file(1)

        mock_regression_output.query.filter.assert_called_once_with(mock_regression_output.id == 1)

    @mock.patch('mod_regression.controllers.serve_file_download')
    @mock.patch('mod_regression.controllers.RegressionTestOutput')
    def test_download_result_file(self, mock_regression_output, mock_serve):
        """
        Test that correct result file triggers serve download.
        """
        from mod_regression.controllers import test_result_file

        response = test_result_file(1)

        mock_regression_output.query.filter.assert_called_once_with(mock_regression_output.id == 1)
        mock_serve.assert_called_once()

    def test_regression_test_deletion_Without_login(self):
        response = self.app.test_client().get('/regression/test/9432/delete')
        self.assertEqual(response.status_code, 302)
        self.assertIn(b'/account/login?next=regression.test_delete', response.data)

    def test_delete_if_will_throw_404(self):
        """
        Check if it will throw an error 404
        :return:
        """
        self.create_user_with_role(self.user.name, self.user.email, self.user.password, Role.admin)

        with self.app.test_client() as c:
            c.post('/account/login', data=self.create_login_form_data(self.user.email, self.user.password))
            response = c.get('/regression/test/9432/delete')
            self.assertEqual(response.status_code, 404)

    def test_delete(self):
        """
        Check it will delete RegressionTest as well as the Customized test
        linked with it
        """

        customized_test = CustomizedTest(test_id=1, regression_id=1)
        g.db.add(customized_test)
        g.db.commit()

        self.create_user_with_role(self.user.name, self.user.email, self.user.password, Role.admin)

        with self.app.test_client() as c:
            c.post('/account/login', data=self.create_login_form_data(self.user.email, self.user.password))

            response = c.get('/regression/test/1/delete')
            self.assertEqual(response.status_code, 200)
            response = c.post(
                '/regression/test/1/delete', data=dict(
                    hidden='yes',
                    submit=True
                )
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(RegressionTest.query.filter(RegressionTest.id == 1).first(), None)
            self.assertEqual(CustomizedTest.query.filter(CustomizedTest.regression_id == 1).first(), None)

    def test_add_category(self):
        """
        Check it will add a category
        """
        self.create_user_with_role(self.user.name, self.user.email, self.user.password, Role.admin)

        with self.app.test_client() as c:
            c.post('/account/login', data=self.create_login_form_data(self.user.email, self.user.password))
            c.post('/regression/category_add',
                   data=dict(category_name="Lost", category_description="And found", submit=True))
            self.assertNotEqual(Category.query.filter(Category.name == "Lost").first(), None)

    def test_add_category_empty(self):
        """
        Check it won't add a category with an empty name
        """
        self.create_user_with_role(self.user.name, self.user.email, self.user.password, Role.admin)

        with self.app.test_client() as c:
            response = c.post(
                '/account/login', data=self.create_login_form_data(self.user.email, self.user.password))
            response = c.post(
                '/regression/category_add', data=dict(category_name="", category_description="And Lost", submit=True))
            self.assertEqual(Category.query.filter(Category.name == "").first(), None)
            self.assertEqual(Category.query.filter(Category.description == "And Lost").first(), None)

    def test_edit_category(self):
        """
        Check it will edit a category
        """
        self.create_user_with_role(self.user.name, self.user.email, self.user.password, Role.admin)

        with self.app.test_client() as c:
            c.post('/account/login', data=self.create_login_form_data(self.user.email, self.user.password))
            new_category = Category(name="C-137", description="Wubba lubba dub dub")
            g.db.add(new_category)
            g.db.commit()
            c.post('/regression/category/1/edit',
                   data=dict(category_name="Sheldon", category_description="That's my spot", submit=True))
            self.assertNotEqual(Category.query.filter(Category.name == "Sheldon").first(), None)

    def test_edit_category_empty(self):
        """
        Check it won't edit a category with an empty name
        """
        self.create_user_with_role(self.user.name, self.user.email, self.user.password, Role.admin)

        with self.app.test_client() as c:
            c.post('/account/login', data=self.create_login_form_data(self.user.email, self.user.password))
            new_category = Category(name="C-137", description="Wubba lubba dub dub")
            g.db.add(new_category)
            g.db.commit()
            c.post('/regression/category/1/edit', data=dict(category_name="", category_description="GG", submit=True))
            self.assertEqual(Category.query.filter(Category.name == "").first(), None)
            self.assertEqual(Category.query.filter(Category.description == "GG").first(), None)
            self.assertNotEqual(Category.query.filter(Category.name == "C-137").first(), None)

    def test_edit_wrong_category(self):
        """
        Check it will throw 404 if trying to edit a category which doesn't exist
        """
        self.create_user_with_role(self.user.name, self.user.email, self.user.password, Role.admin)

        with self.app.test_client() as c:
            c.post('/account/login', data=self.create_login_form_data(self.user.email, self.user.password))
            new_category = Category(name="C-137", description="Wubba lubba dub dub")
            g.db.add(new_category)
            g.db.commit()
            response = c.post(
                'regression/category/1729/edit',
                data=dict(category_name="Sheldon", category_description="That's my spot", submit=True)
            )
            self.assertEqual(response.status_code, 404)

    def test_add_test(self):
        """
        Check it will add a regression test
        """
        self.create_user_with_role(self.user.name, self.user.email, self.user.password, Role.admin)

        with self.app.test_client() as c:
            c.post('/account/login', data=self.create_login_form_data(self.user.email, self.user.password))
            c.post('/regression/test/new', data=dict(
                sample_id=1,
                command="-autoprogram -out=ttxt -latin1 -2",
                input_type="file",
                output_type="file",
                category_id=1,
                expected_rc=25,
                submit=True,
            ))
            self.assertNotEqual(RegressionTest.query.filter(RegressionTest.id == 3).first(), None)

    def test_add_test_empty_erc(self):
        """
        Check it will not add a regression test with empty Expected Runtime Code
        """
        self.create_user_with_role(self.user.name, self.user.email, self.user.password, Role.admin)

        with self.app.test_client() as c:
            c.post('/account/login', data=self.create_login_form_data(self.user.email, self.user.password))
            c.post('/regression/test/new', data=dict(
                sample_id=1,
                command="-autoprogram -out=ttxt -latin1 -2",
                input_type=InputType.file,
                output_type=OutputType.file,
                category_id=1,
                submit=True,
            ))
            self.assertEqual(RegressionTest.query.filter(RegressionTest.id == 3).first(), None)

    def test_category_deletion_without_login(self):
        response = self.app.test_client().get('/regression/category/9432/delete')
        self.assertEqual(response.status_code, 302)
        self.assertIn(b'/account/login?next=regression.category_delete', response.data)

    def test_category_delete_if_will_throw_404(self):
        """
        Check if it will throw an error 404
        :return:
        """
        self.create_user_with_role(self.user.name, self.user.email, self.user.password, Role.admin)

        with self.app.test_client() as c:
            c.post('/account/login', data=self.create_login_form_data(self.user.email, self.user.password))

            response_regression = c.get('/regression/category/9432/delete')
            self.assertEqual(response_regression.status_code, 404)

    def test_category_delete(self):
        """
        Check it will delete the Category
        :return:
        """

        self.create_user_with_role(self.user.name, self.user.email, self.user.password, Role.admin)

        with self.app.test_client() as c:
            c.post('/account/login', data=self.create_login_form_data(self.user.email, self.user.password))
            response = c.get('/regression/category/1/delete')
            self.assertEqual(response.status_code, 200)
            response = c.post('/regression/category/1/delete', data=dict(
                hidden='yes',
                submit=True
            ))
            self.assertEqual(response.status_code, 302)

    def test_edit_test(self):
        """
        Check it will edit a regression test
        """
        self.create_user_with_role(self.user.name, self.user.email, self.user.password, Role.admin)

        with self.app.test_client() as c:
            c.post('/account/login', data=self.create_login_form_data(self.user.email, self.user.password))
            c.post('/regression/test/2/edit', data=dict(
                sample_id=1,
                command="-demogorgans",
                input_type="file",
                output_type="file",
                category_id=2,
                expected_rc=25,
                submit=True,
            ))
            self.assertNotEqual(RegressionTest.query.filter(RegressionTest.command == "-demogorgans").first(), None)

            category = Category.query.filter(Category.id == 1).first()
            for i in category.regression_tests:
                self.assertNotEqual(i.id, 2)
            category = Category.query.filter(Category.id == 2).first()
            for i in category.regression_tests:
                if i.id == 2:
                    break
            else:
                self.fail("No tests in category")

    def test_edit_test_empty_erc(self):
        """
        Check it will not edit a regression test with empty Expected Runtime Code
        """
        self.create_user_with_role(self.user.name, self.user.email, self.user.password, Role.admin)

        with self.app.test_client() as c:
            c.post('/account/login', data=self.create_login_form_data(self.user.email, self.user.password))
            c.post('/regression/test/1/edit', data=dict(
                sample_id=1,
                command="-demogorgans",
                input_type="file",
                output_type="file",
                category_id=2,
                submit=True,
            ))
            self.assertEqual(RegressionTest.query.filter(RegressionTest.command == "-demogorgans").first(), None)

            category = Category.query.filter(Category.id == 1).first()

            for i in category.regression_tests:
                if i.id == 1:
                    break
            else:
                self.fail("No tests in category")
            category = Category.query.filter(Category.id == 2).first()
            for i in category.regression_tests:
                self.assertNotEqual(i.id, 1)

    def test_edit_wrong_test(self):
        """
        Check it will throw 404 if trying to edit a regression test which doesn't exist
        """
        self.create_user_with_role(self.user.name, self.user.email, self.user.password, Role.admin)

        with self.app.test_client() as c:
            c.post('/account/login', data=self.create_login_form_data(self.user.email, self.user.password))
            response_regression = c.post('/regression/test/42/edit', data=dict(
                sample_id=1,
                command="-demogorgans",
                input_type="file",
                output_type="file",
                expected_rc=25,
                category_id=2,
                submit=True,
            ))
            self.assertEqual(response_regression.status_code, 404)

    def test_edit_test_same_category(self):
        """
        Check it won't create problems edit a regression test and not changing its category
        """
        self.create_user_with_role(self.user.name, self.user.email, self.user.password, Role.admin)

        with self.app.test_client() as c:
            c.post('/account/login', data=self.create_login_form_data(self.user.email, self.user.password))
            c.post('/regression/test/2/edit', data=dict(
                sample_id=1,
                command="-demogorgans",
                input_type="file",
                output_type="file",
                category_id=1,
                expected_rc=25,
                submit=True,
            ))
            self.assertNotEqual(RegressionTest.query.filter(RegressionTest.command == "-demogorgans").first(), None)

            category = Category.query.filter(Category.id == 1).first()
            for i in category.regression_tests:
                if i.id == 2:
                    break
            else:
                self.fail("No tests in category")

    def test_if_test_regression_view_throws_a_not_found_error(self):
        """
        Check if the test doesn't exist and will throw an error 404
        """
        response = self.app.test_client().get('regression/test/1337/view')
        self.assertEqual(response.status_code, 404)

    def test_if_test_toggle_view_throws_a_not_found_error(self):
        """
        Check if the test toggle doesn't exist and will throw an error 404
        """
        self.create_user_with_role(self.user.name, self.user.email, self.user.password, Role.admin)

        with self.app.test_client() as c:
            c.post('/account/login', data=self.create_login_form_data(self.user.email, self.user.password))

            response = c.get('regression/test/1337/toggle')
            self.assertEqual(response.status_code, 404)

    def test_sample_view(self):
        """
        Test if it'll return a valid sample
        """
        response = self.app.test_client().get('/regression/sample/1')
        sample = Sample.query.filter(Sample.id == 1).first()
        self.assertEqual(response.status_code, 200)
        self.assert_context('sample', sample)

    def test_sample_view_nonexistent(self):
        """
        Test if it'll return a valid sample
        """
        response = self.app.test_client().get('/regression/sample/13423423')
        self.assertEqual(response.status_code, 404)
