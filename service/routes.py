######################################################################
# Copyright 2016, 2022 John J. Rofrano. All Rights Reserved.
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

# spell: ignore Rofrano jsonify restx dbname
"""
Product Store Service with UI
"""
from flask import jsonify, request, abort
from flask import url_for  # noqa: F401 pylint: disable=unused-import
from service.models import Category, Product
from service.common import status  # HTTP Status Codes
from service.common.error_handlers import not_found  # Error handlers
from . import app


######################################################################
# H E A L T H   C H E C K
######################################################################
@app.route("/health")
def healthcheck():
    """Let them know our heart is still beating"""
    return jsonify(status=200, message="OK"), status.HTTP_200_OK


######################################################################
# H O M E   P A G E
######################################################################
@app.route("/")
def index():
    """Base URL for our service"""
    return app.send_static_file("index.html")


######################################################################
#  U T I L I T Y   F U N C T I O N S
######################################################################
def check_content_type(content_type):
    """Checks that the media type is correct"""
    if "Content-Type" not in request.headers:
        app.logger.error("No Content-Type specified.")
        abort(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Content-Type must be {content_type}",
        )

    if request.headers["Content-Type"] == content_type:
        return

    app.logger.error("Invalid Content-Type: %s", request.headers["Content-Type"])
    abort(
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        f"Content-Type must be {content_type}",
    )


def inject_not_found_method(product_id, method):
    """
    Injects the product id and request method into a not found response
    """
    error_msg = f"No product with {product_id} exists in the DB for {method}"
    app.logger.debug(error_msg)
    return error_msg


######################################################################
# C R E A T E   A   N E W   P R O D U C T
######################################################################
@app.route("/products", methods=["POST"])
def create_products():
    """
    Creates a Product
    This endpoint will create a Product based the data in the body that is posted
    """
    app.logger.info("Request to Create a Product...")
    check_content_type("application/json")

    data = request.get_json()
    app.logger.info("Processing: %s", data)
    product = Product()
    product.deserialize(data)
    product.create()
    app.logger.info("Product with new id [%s] saved!", product.id)

    message = product.serialize()

    location_url = url_for("get_products", product_id=product.id, _external=True)
    return jsonify(message), status.HTTP_201_CREATED, {"Location": location_url}


######################################################################
# L I S T   A L L   P R O D U C T S
######################################################################
@app.route("/products", methods=["GET"])
def list_products():
    """Returns a list of Products"""

    if "name" in request.args:
        query_name = request.args.get("name")
        app.logger.info("Request to list Products by name: %s", query_name)
        products = Product.find_by_name(query_name)
    elif "category" in request.args:
        category = request.args.get("category")
        app.logger.info("Request to list by category: %s", category)
        category_val = getattr(Category, category.upper())
        products = Product.find_by_category(category_val)
    elif "available" in request.args:
        available_status = bool(request.args.get("available"))
        app.logger.info("Request to list by availability: %s", available_status)
        products = Product.find_by_availability(available_status)
    else:
        app.logger.info("Request to list all Products")
        # Retrieve all the products.
        products = Product.all()

    # Serialize all the products.
    serialized_products = [product.serialize() for product in products]

    # Log the number of products being returned.
    app.logger.info(f"Number of Products: {len(serialized_products)}")

    return serialized_products, status.HTTP_200_OK


######################################################################
# R E A D   A   P R O D U C T
######################################################################
@app.route("/products/<product_id>", methods=["GET"])
def get_products(product_id):
    """
    Reads a product from the database given a product ID
    """
    found = Product.find(product_id)
    if not found:
        # return {}, status.HTTP_404_NOT_FOUND
        return not_found(f"No product with {product_id} exists in the DB")

    serialized_prod = found.serialize()
    return serialized_prod, status.HTTP_200_OK


######################################################################
# U P D A T E   A   P R O D U C T
######################################################################
@app.route("/products/<product_id>", methods=["PUT"])
def update_products(product_id):
    """
    Update a Product
    This endpoint updates a product based on the body that is posted.
    """
    app.logger.info("Request to Update a product with id [%s]", product_id)
    check_content_type("application/json")

    # Retrieve the Product.
    old_product = Product.find(product_id)
    if not isinstance(old_product, Product):
        # return not_found(f"No product with {product_id} exists in the DB")
        return not_found(inject_not_found_method(product_id, "UPDATE"))

    # Update the product.
    data = request.get_json()
    app.logger.info("Processing Update for: %s", data)
    updated_product = Product()
    updated_product = updated_product.deserialize(data)
    old_product.name = updated_product.name
    old_product.description = updated_product.description
    old_product.price = updated_product.price
    old_product.available = updated_product.available
    old_product.category = updated_product.category
    old_product.update()

    # Return the serialized version of the updated product.
    return old_product.serialize(), status.HTTP_200_OK


######################################################################
# D E L E T E   A   P R O D U C T
######################################################################
@app.route("/products/<int:product_id>", methods=["DELETE"])
def delete_products(product_id):
    """
    Delete a Product

    This endpoint will delete a Product based on the product ID received.
    """
    app.logger.info("Request to Delete a product with id [%s]", product_id)

    # Retrieve the produt to be deleted.
    product = Product.find(product_id)
    if not isinstance(product, Product):
        return not_found(inject_not_found_method(product_id, "Delete"))

    # Delete the product if found.
    product.delete()
    return "", status.HTTP_204_NO_CONTENT
