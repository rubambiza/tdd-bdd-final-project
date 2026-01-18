######################################################################
# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################
"""
Product API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
  codecov --token=$CODECOV_TOKEN

  While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_service.py:TestProductService
"""
import os
import logging
from decimal import Decimal
from unittest import TestCase
from urllib.parse import quote_plus
from service import app
from service.common import status
from service.models import db, init_db, Product
from tests.factories import ProductFactory


# Disable all but critical errors during normal test run
# uncomment for debugging failing tests
# logging.disable(logging.CRITICAL)

# DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///../db/test.db')
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
BASE_URL = "/products"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductRoutes(TestCase):
    """Product Service tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    ############################################################
    # Utility function to bulk create products
    ############################################################
    def _create_products(self, count: int = 1) -> list:
        """Factory method to create products in bulk"""
        products = []
        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(BASE_URL, json=test_product.serialize())
            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, "Could not create test product"
            )
            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)
        return products

    ############################################################
    #  T E S T   C A S E S
    ############################################################
    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"Product Catalog Administration", response.data)

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data['message'], 'OK')

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------
    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()
        logging.debug("Test Product: %s", test_product.serialize())
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

        #
        # Uncomment this code once READ is implemented
        #

        # # Check that the location header was correct
        response = self.client.get(location)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

    def test_create_product_with_no_name(self):
        """It should not Create a Product without a name"""
        product = self._create_products()[0]
        new_product = product.serialize()
        del new_product["name"]
        logging.debug("Product no name: %s", new_product)
        response = self.client.post(BASE_URL, json=new_product)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        """It should not Create a Product with no Content-Type"""
        response = self.client.post(BASE_URL, data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        """It should not Create a Product with wrong Content-Type"""
        response = self.client.post(BASE_URL, data={}, content_type="plain/text")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    #
    # ADD YOUR TEST CASES HERE
    #
    def test_get_product(self):
        """It should retrieve a product from the database."""
        # Create a product
        test_product = self._create_products(1)[0]

        # Make a Get request for the product
        response = self.client.get(f"{BASE_URL}/{test_product.id}")

        # Assert that the retrieved result matches the original product.
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

    def test_get_invalid_product(self):
        """It should throw a error when getting an invalid Product"""
        # Create a product
        test_product = self._create_products(1)[0]

        # Make a Get request for an invalid product
        test_product.id = -1
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_product(self):
        """It should Update an existing product."""
        # Signature: PUT /products/{id}
        test_product = ProductFactory()

        # Create the product.
        response = self.client.post(
                f"{BASE_URL}",
                json=test_product.serialize()
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Update the product.
        updated_desc = "New description"
        new_product = response.get_json()
        new_product["description"] = updated_desc
        update_resp = self.client.put(
                f"{BASE_URL}/{new_product['id']}",
                json=new_product
            )
        self.assertEqual(update_resp.status_code, status.HTTP_200_OK)

        # Check that the description of the product was updated as expected.
        updated_product = update_resp.get_json()
        self.assertEqual(updated_product['description'], updated_desc)

    def test_update_invalid_product(self):
        """It should not Update a Product does not exist."""
        # Signature: PUT /products/{id}
        test_product = ProductFactory()

        # Create the product.
        response = self.client.post(
                f"{BASE_URL}",
                json=test_product.serialize()
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Update the product.
        updated_id = -1
        new_product = response.get_json()
        new_product["id"] = updated_id
        update_resp = self.client.put(
                f"{BASE_URL}/{new_product['id']}",
                json=new_product
            )
        self.assertEqual(update_resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_product(self):
        """It should Delete an existing Product."""
        # Signature: DELETE /products/{id}
        products = self._create_products(5)

        # Count the initial number of products and get the first one.
        count = self.get_product_count()
        test_product = products[0]

        # Delete the product and check the status code.
        response = self.client.delete(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.get_json(), None)

        # Test that a query for the deleted product returns not found.
        query_resp = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(query_resp.status_code, status.HTTP_404_NOT_FOUND)

        # Check that there is one fewer product after deletion.
        updated_count = self.get_product_count()
        self.assertNotEqual(count, updated_count)

    def test_delete_invalid_product(self):
        """It should not Delete a Product that does not exist"""
        # Signature: DELETE /products/{id}
        products = self._create_products(5)

        # Get the first product for testing.
        test_product = products[0]
        test_product.id = 0

        # Delete the product and check the status code.
        response = self.client.delete(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_product_list(self):
        """It should list all the Products in the database."""
        #     Signature: GET /products
        # Create the products
        self._create_products(5)

        # Retrieve and check the cardinality of all the products.
        response = self.client.get(f"{BASE_URL}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 5)

    def test_get_product_by_name(self):
        """It should list all Products with a given name."""
        # Create the products
        products = self._create_products(5)

        # Get the first product name for testing.
        test_name = products[0].name

        # Count the products with the same name.
        count = len([product for product in products if product.name == test_name])

        # Retrieve products with the given name in the database.
        response = self.client.get(
            BASE_URL, query_string=f"name={quote_plus(test_name)}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that the retrieved data matches the expected count and details.
        data = response.get_json()
        self.assertEqual(len(data), count)
        for product in data:
            self.assertEqual(product["name"], test_name)

    def test_get_product_by_category(self):
        """It should list all Products by a given category."""
        # Create the products
        products = self._create_products(5)

        # Get the first product name for testing.
        test_category = products[0].category

        # Check and count all products that match the category.
        found = [product for product in products if product.category == test_category]
        found_count = len(found)

        # Log the found products and count details.
        logging.debug("Count: %d\n, All Products %s", found_count, found)

        # Retrieve products with the given category in the database.
        response = self.client.get(
            BASE_URL, query_string=f"category={test_category.name}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that the retrieved data matches the expected count and details.
        data = response.get_json()
        self.assertEqual(len(data), found_count)
        for product in data:
            self.assertEqual(product["category"], test_category.name)

    def test_get_product_by_availability(self):
        """It should list all Products by availability."""
        # Create the products
        products = self._create_products(5)

        # Check and count all products that match the availability.
        found = [product for product in products if product.available]
        found_count = len(found)

        # Log the found products and count details.
        logging.debug("Count: %d\n, All Products %s", found_count, found)

        # Retrieve products with the given availability in the database.
        response = self.client.get(
            BASE_URL, query_string="available=True"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that the retrieved data matches the expected count and details.
        data = response.get_json()
        self.assertEqual(len(data), found_count)
        for product in data:
            self.assertEqual(product["available"], True)

    # def test_create_product_with_invalid_availability(self):
    #     """It should throw a data validation error when creating product with wrong availability."""
    #     test_product = ProductFactory()
    #     test_product.available = 14.5
    #     serialized_prod = test_product.serialize()
    #     logging.debug("Test Product with Invalid Availability: %s", serialized_prod)
    #     with self.assertRaises(DataValidationError):
    #         serialized_prod.deserialize()

    ######################################################################
    # Utility functions
    ######################################################################

    def get_product_count(self):
        """save the current number of products"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        # logging.debug("data = %s", data)
        return len(data)
