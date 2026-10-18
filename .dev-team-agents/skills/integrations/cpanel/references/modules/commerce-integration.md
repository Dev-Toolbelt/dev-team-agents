<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Commerce Integration

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **SSL Certificates**: [`Market::cancel_pending_ssl_certificate`](#market-cancel-pending-ssl-certificate), [`Market::get_certificate_status_details`](#market-get-certificate-status-details), [`Market::get_pending_ssl_certificates`](#market-get-pending-ssl-certificates), [`Market::get_provider_specific_dcv_constraints`](#market-get-provider-specific-dcv-constraints), [`Market::get_ssl_certificate_if_available`](#market-get-ssl-certificate-if-available), [`Market::process_ssl_pending_queue`](#market-process-ssl-pending-queue), [`Market::request_ssl_certificates`](#market-request-ssl-certificates)
- **Market Integration**: [`Market::create_shopping_cart`](#market-create-shopping-cart), [`Market::create_shopping_cart_non_ssl`](#market-create-shopping-cart-non-ssl), [`Market::get_all_products`](#market-get-all-products), [`Market::get_build_cart_url`](#market-get-build-cart-url), [`Market::get_completion_url`](#market-get-completion-url), [`Market::get_license_info`](#market-get-license-info), [`Market::get_login_url`](#market-get-login-url), [`Market::get_product_info`](#market-get-product-info), [`Market::get_providers_list`](#market-get-providers-list), [`Market::set_status_of_pending_queue_items`](#market-set-status-of-pending-queue-items), [`Market::set_url_after_checkout`](#market-set-url-after-checkout), [`Market::validate_login_token`](#market-validate-login-token)

## SSL Certificates

<a id="market-cancel-pending-ssl-certificate"></a>
### `Market::cancel_pending_ssl_certificate` — Delete an order

`GET /execute/Market/cancel_pending_ssl_certificate` · RW · rollback: none · since cPanel 56

This function cancels an order and removes the polling for a pending certificate.

**Parameters**

- `order_item_id` · **required** · string · e.g. `10427508` — The ID of the ordered item to cancel.
- `provider` · **required** · string · e.g. `cPStore` — The cPanel Market provider's name.

**Returns** `data`: array of object — An object containing order information.

- *(array of objects)*
  - `created_time` (integer <unix_timestamp>) — When the system created the order.
  - `csr` (string <base64 certificate>) — The text of the Certificate Request (CSR).
  - `domains` (array of string <domain>) — A list of domains on the certificate.
  - `expired` (integer (`0`, `1`)) — Whether the system has deleted the item from the pending queue.; `1` - Deleted.; `0` - **Not** deleted.
  - `first_poll_time` (integer <unix_timestamp>) — The first time that the system polled the provider for the certificate.
  - `last_poll_time` (integer <unix_timestamp>) — The last time that the system polled the provider for the certificate.
  - `last_status_code` (string (`CertificateNotFound`, `RequiresApproval`, `OrderCanceled`, `OrderItemCanceled`)) — The last status code of the order.; `CertificateNotFound` - The system cannot locate the specified certificate.; `RequiresApproval` - The specified certificate requires approval.; `OrderCanceled` - The system cancelled t
  - `order_id` (string) — The ID of the order.
  - `order_item_id` (string) — The ID of the ordered item.
  - `product_id` (string) — The product's ID.
  - `provider` (string) — The cPanel Market provider's name.
  - `status` (string (`confirmed`, `unconfirmed`)) — The status of the order.; `confirmed` - Payment confirmed.; `unconfirmed` - Payment **not** confirmed.
  - `support_uri` (string <uri>) — The URI of the cPanel Market Provider's support site.
  - `vhost_names` (array of string) — A list of virtual host names.

```bash
uapi --output=jsonpretty \
  --user=username \
  Market \
  cancel_pending_ssl_certificate \
  provider='cPStore' \
  order_item_id='10427508'
```

<a id="market-get-certificate-status-details"></a>
### `Market::get_certificate_status_details` — Return provider's SSL certificate request status

`GET /execute/Market/get_certificate_status_details` · RO · since cPStore 76

This function returns the status of an SSL certificate request. The returns include actionable URLs for users to expedite the validation process, if applicable. Important: Because this function returns data from a dynamic source, the returns in each object can vary.

**Parameters**

- `order_item_id` · **required** · integer · e.g. `1234567890` — The order ID that the cPanel Market provider assigned.
- `provider` · **required** · string · e.g. `cPStore` — The cPanel Market provider's name.

**Returns** `data`: object

- `actionUrls` (object) — An object that contains actionable URLs.
  - `evClickThroughStatus` (string <url>) — A URL that a user can use to expedite the validation process for Extended Validation (EV) certificates.
  - `ovCallbackStatus` (string <url>) — A URL that a user can use to expedite the validation process for Organization Validated (OV) certificates.
- `domain_details` (object) — An object that contains information about the domain.
  - `domain` (string <domain>) — The Fully Qualified Domain Name (FQDN) that the function queries.
  - `status` (string (`VALIDATED`, `NOTVALIDATED`, `AWAITINGBRAND`)) — The status of the domain's certificate.; `VALIDATED` - The domain has been validated.; `NOTVALIDATED` - The domain has **not** been validated.; `AWAITINGBRAND` - The domain has **not** been validated, and is awaiting bra
- `status_details` (object) — An object that contains specific information about the validation process.
  - `brandValStatus` (string (`not applicable`, `not-completed`, `completed`, `in-progress`)) — Whether the brand validation status has completed.; `not applicable` - This is **not** applicable for the certificate.; `not-completed` - The certificate's brand validation is **not** complete.; `completed` - The certifi
  - `certificateStatus` (string (`not applicable`, `not-completed`, `completed`, `in-progress`)) — Whether the provider has issued the SSL certificate.; `not applicable` - This is **not** applicable for the certificate.; `not-completed` - The certificate's issue is **not** completed.; `completed` - The provider has is
  - `csrStatus` (string (`not applicable`, `not-completed`, `completed`, `in-progress`)) — Whether the certificate signing request (CSR) has completed.; `not applicable` - This is **not** applicable for the certificate.; `not-completed` - The CSR for the certificate is **not** complete.; `completed` - The CSR 
  - `dcvStatus` (string (`not applicable`, `not-completed`, `completed`, `in-progress`)) — Whether Domain Control Validation (DCV) has completed.; `not applicable` - This is **not** applicable for the certificate.; `not-completed` - The DCV for the certificate is **not** complete.; `completed` - The DCV for th
  - `evClickThroughStatus` (string (`not applicable`, `not-completed`, `completed`, `in-progress`)) — Whether every requirement for the EV certificate has completed.; `not applicable` - This is **not** applicable for the certificate.; `not-completed` - The EV certificate's requirements check is **not** complete.; `comple
  - `freeDVUPStatus` (string (`not applicable`, `not-completed`, `completed`, `in-progress`)) — Whether every requirement for the Domain Validated (DV) certificate has completed.; `not applicable` - This is **not** applicable for the certificate.; `not-completed` - The DV certificate's requirements check is **not**
  - `organizationValidationStatus` (string (`not applicable`, `not-completed`, `completed`, `in-progress`)) — Whether every requirement for the OV certificate has completed.; `not applicable` - This is **not** applicable for the certificate.; `not-completed` - The OV certificate's requirements check is **not** complete.; `comple
  - `ovCallbackStatus` (string (`not applicable`, `not-completed`, `completed`, `in-progress`)) — Whether the Certificate Authority (CA) has verified the organization's validity via a phone call.; `not applicable` - This is **not** applicable for the certificate.; `not-completed` - The CA has **not** verified the org
  - `validationStatus` (string (`not applicable`, `not-completed`, `completed`, `in-progress`)) — Whether the validation process has completed.; `not applicable` - This is **not** applicable for the certificate.; `not-completed` - The certificate's validation is **not** complete.; `completed` - The certificate's vali

```bash
uapi --output=jsonpretty \
  --user=username \
  Market \
  get_certificate_status_details \
  order_item_id='1234567890' \
  provider='cPStore'
```

<a id="market-get-pending-ssl-certificates"></a>
### `Market::get_pending_ssl_certificates` — Return provider's pending SSL certificates

`GET /execute/Market/get_pending_ssl_certificates` · RO · since cPanel 56

This function lists all pending SSL certificates from a cPanel Market provider for which the system currently polls.

**Parameters**

- `provider` · **required** · string · e.g. `cPStore` — The cPanel Market provider's name.

**Returns** `data`: array of object — An array of objects that contain information about each certificate for which the system polls the provider.

- *(array of objects)*
  - `created_time` (integer <unix_timestamp>) — When the system placed the order.
  - `csr` (string <base64 certificate>) — The certificate signing request's (CSR) text.
  - `domains` (array of string <domain>) — The domains on the certificate.
  - `expired` (integer (`0`, `1`)) — Whether the pending queue item has been deleted.; `1` - Deleted.; `0` - **Not** deleted.
  - `first_poll_time` (integer <unix_timestamp>) — The first time that the system polled the provider for the certificate.
  - `identity_verification` (object) — hash that contains information to verify an OV or EV certificate request.
  - `certificate_id` (string) — The certificate ID.
  - `last_poll_time` (integer <unix_timestamp>) — The last time that the system polled the provider for the certificate.
  - `last_status_code` (string (`CertificateNotFound`, `RequiresApproval`, `OrderCanceled`, `OrderItemCanceled`)) — The last status code of the order.
  - `order_id` (string) — The ID of the order.
  - `order_item_id` (string) — The ID of the ordered item.
  - `originating_certificate_id` (string) — For a re-issued certificate, the ID of the certificate that it descends from.
  - `parent_cert_expiry` (integer <unix_timestamp>) — The expiration of the parent subscription certificate, as a Unix timestamp.
  - `product_id` (string) — The product's ID.
  - `provider` (string) — The cPanel Market provider's name.
  - `status` (string) — The status of the order.; `confirmed` - Payment confirmed.; `unconfirmed` - Payment not confirmed.
  - `support_uri` (string <url>) — The URI of the cPanel Market Provider's support site.
  - `vhost_names` (array of string <domain>) — The virtual host domains on the certificate.

```bash
uapi --output=jsonpretty \
  --user=username \
  Market \
  get_pending_ssl_certificates \
  provider='cPStore'
```

<a id="market-get-provider-specific-dcv-constraints"></a>
### `Market::get_provider_specific_dcv_constraints` — Return provider's DCV filename requirements

`GET /execute/Market/get_provider_specific_dcv_constraints` · RO · since cPanel 62

This function returns the provider's filename requirements for Domain Control Validation (DCV) checks.

**Parameters**

- `provider` · **required** · string · e.g. `cPStore` — The cPanel Market provider's name.

**Returns** `data`: object

- `dcv_file_allowed_characters` (array of string) — An array that lists the characters which the provider allows in the DCV check file's filename.
- `dcv_file_extension` (string) — The DCV check file extension that the provider requires.
- `dcv_file_random_character_count` (integer) — The number of characters that the provider allows in the DCV check file's filename.
- `dcv_file_relative_path` (string <path>) — The path to the DCV check file, relative to the domain's document root directory.
- `dcv_max_redirects` (integer) — The maximum number of HTTP redirects the provider allows.
- `dcv_user_agent_string` (string) — The user agent string that the system will use for the imitated local DCV check.

```bash
uapi --output=jsonpretty \
  --user=username \
  Market \
  get_provider_specific_dcv_constraints \
  provider='cPStore'
```

<a id="market-get-ssl-certificate-if-available"></a>
### `Market::get_ssl_certificate_if_available` — Return provider's available SSL certificates

`GET /execute/Market/get_ssl_certificate_if_available` · RO · since cPanel 56

This function retrieves SSL certificates when they are available from the cPanel Market provider.

**Parameters**

- `order_item_id` · **required** · string · e.g. `8675309` — The order item for which to poll.
- `provider` · **required** · string · e.g. `cPStore` — The cPanel Market provider's name.

**Returns** `data`: object

- `certificate_pem` (string <base64 certificate>) — The certificate's text.; `null` - The certificate is not available.; A certificate file in [Base64 PEM](https://en.wikipedia.org/wiki/Privacy-Enhanced_Mail) format.
- `encrypted_action_urls` (object) — An object that contains encrypted URLs a user must click to complete their SSL certificate order.
  - `evClickThroughStatus` (string) — A URL the user must click to electronically sign an agreement for their Extended Validation (EV) certificate.; An encrypted URL.; `null` - No action required.
  - `ovCallbackStatus` (string) — URL the user must click to verify their identity by phone to complete their Organization Validation (OV) certificate order.; An encrypted URL.; `null` - No action required.
- `status_code` (string) — The status code of the certificate.
- `status_message` (string) — An error message from the certificate provider.

```bash
uapi --output=jsonpretty \
  --user=username \
  Market \
  get_ssl_certificate_if_available \
  provider='cPStore' \
  order_item_id='8675309'
```

<a id="market-process-ssl-pending-queue"></a>
### `Market::process_ssl_pending_queue` — Start processing pending queue's SSL certificates

`GET /execute/Market/process_ssl_pending_queue` · RW · rollback: none · since cPanel 56

This function manually processes the cPanel Market's SSL certificate request pending queue.

**Returns** `data`: array of object — Information about each certificate request in the pending queue.

- *(array of objects)*
  - `certificate_id` (string) — The certificate ID.
  - `certificate_pem` (string <base64 certificate>) — The text of the certificate, if available.; `null` - The certificate is not available.
  - `created_time` (integer <unix_timestamp>) — When the system placed the order.
  - `csr` (string <base64 certificate>) — The Certificate Signing Request's (CSR's) text.
  - `deleted` (integer (`0`, `1`)) — Whether the system has deleted the item from the pending queue.; `0` - Deleted.; `1` - **Not** deleted.
  - `domains` (array of string <domain>) — A list of domains that the certificate request covers.
  - `expired` (integer (`0`, `1`)) — Whether the system has deleted the item from the pending queue.; `1` - Deleted.; `0` - **Not** deleted.
  - `first_poll_time` (integer <unix_timestamp>) — The first time that the system polled the provider for the certificate.
  - `installed` (integer (`0`, `1`)) — Whether the system installed the certificate.; `1` - Installed.; `0` - **Not** installed.
  - `last_poll_time` (integer <unix_timestamp>) — The last time that the system polled the provider for the certificate.
  - `last_status_code` (string (`CertificateNotFound`, `RequiresApproval`, `OrderCanceled`, `OrderItemCanceled`)) — The last status code of the order.; `CertificateNotFound` - The system cannot locate the specified certificate.; `RequiresApproval` - The specified certificate requires approval.; `OrderCanceled` - The system canceled th
  - `last_status_message` (string) — An error message from the certificate provider.
  - `order_id` (string) — A unique identifier for the order.
  - `order_item_id` (string) — A unique identifier of each item in the order.
  - `originating_certificate_id` (string) — For a re-issued certificate, the ID of the certificate that it descends from.
  - `parent_cert_expiry` (integer <unix_timestamp>) — The expiration of the parent subscription certificate, as a Unix timestamp.
  - `product_id` (string) — An identifier for a given product.
  - `provider` (string) — The cPanel Market provider's name.
  - `status` (string (`confirmed`, `unconfirmed`)) — The status of the order.; `confirmed` - Payment confirmed.; `unconfirmed` - Payment **not** confirmed.
  - `vhost_names` (array of string <domain>) — A list of virtual host names.

```bash
uapi --output=jsonpretty \
  --user=username \
  Market \
  process_ssl_pending_queue
```

<a id="market-request-ssl-certificates"></a>
### `Market::request_ssl_certificates` — Request SSL certificate order

`GET /execute/Market/request_ssl_certificates` · RW · rollback: none · since cPanel 56

This function submits a request for a certificate order to the cPanel Market provider.

**Parameters**

- `access_token` · **required** · string · e.g. `725431a1-d5bc-11e5-a28b-8b0e09a93f05` — The access token for the session to the cPanel Market provider.
- `certificate` · **required** · JSON-encoded · object — A JSON-encoded string that contains the details of the certificate. Note: To request multiple certificates, duplicate or increment the parameter name. For example, to request three certificates, use the `certificate` parameter multiple times or use the `certificate-1`, `certificate-2`, and `certificate-3` parameters.
  - `price` (number <currency>) — The certificate's price.
  - `product_id` (string) — The product's ID.
  - `subject_names` (array of object or array of string) — An array of strings or array of objects containing the certificate's subject names: **For HTTP-based DCV only:** Use an array of strings that contains `dNSName` and the domain.
  - `validity_period` (array of string) — The period of time the certificate will remain valid.
  - `vhost_names` (array of string) — A comma-separated list of web virtual hosts (vhosts) for which the system will install the certificate.
- `provider` · **required** · string · e.g. `cPStore` — The cPanel Market provider's name.
- `identity_verification` · optional · JSON-encoded · object — An object containing the required information for an EV or OV certificate. This information depends on the provider of the certificate. Note: The function returns this object for OV or EV certificate requests.
- `url_after_checkout` · optional · string <url> · e.g. `http://checkout.example.com` — The URL to send the browser after the user checks out. Note: This URL does **not** contain a query string.

**Returns** `data`: object

- `certificates` (object) — Information about each certificate in the order.
  - `key_id` (string) — The private key's ID.
  - `order_item_id` (integer) — The ID of the ordered item.
- `checkout_url` (string <url>) — The URL that the cPanel Market provider uses to process payment.
- `order_id` (integer) — The order ID that the cPanel Market provider assigned.

```bash
uapi --output-jsonpretty --user=username Market request_ssl_certificates access_token='725431a1-d5bc-11e5-a28b-8b0e09a93f05' certificate='{"price":"6","product_id":"143","subject_names":[{"dNSName":"example.com"},{"dNSName":"example.org"}],"validity_period":["1, \"year\""],"vhost_names":["example.com"]}' provider='cPStore'
```

## Market Integration

<a id="market-create-shopping-cart"></a>
### `Market::create_shopping_cart` — Create shopping cart

`GET /execute/Market/create_shopping_cart` · RW · rollback: none · since cPanel 62

This function creates a shopping cart with which the system sends an order to the cPanel Store. Typically, the system will send shopping cart orders for SSL certificates to UAPI’s `Market::request_ssl_certificates` function.

**Parameters**

- `access_token` · **required** · string <uuid> · e.g. `1a676e6f-99fc-11e6-9ab6-e60a769b73bc` — The access token to connect to the provider.
- `item` · **required** · array of string <json> — The items to add to the shopping cart. **Note**: The value is a JSON string. This object has one required key, `product_id`, which is a string. The other keys/values in this object vary depending on the provider.
- `provider` · **required** · string · e.g. `cPStore` — The cPanel Market provider’s name.
- `url_after_checkout` · **required** · string <url> · e.g. `http://www.example.com/thenextplace` — The location to which the provider directs the user after the checkout process is complete.

**Returns** `data`: object

- `checkout_url` (string <url>) — The location of the provider’s check out page.
- `order_id` (string) — The order’s ID.
- `order_items` (array of object) — An array of objects that contain information about Items in the shopping cart.

```bash
uapi --output=jsonpretty \
  --user=username \
  Market \
  create_shopping_cart \
  provider='cPStore' \
  access_token='1a676e6f-99fc-11e6-9ab6-e60a769b73bc' \
  url_after_checkout='http://www.example.com/thenextplace' \
  item='{"product_id":123456,"provider-specfic-key":"provider-specfic-value","another-provider-specfic-key":"another-provider-specfic-value"}' item='{"product_id":123457,"provider-specfic-key":"provider-specfic-value","another-provider-specfic-key":"another-provider-specfic-value"}'
```

<a id="market-create-shopping-cart-non-ssl"></a>
### `Market::create_shopping_cart_non_ssl` — Create shopping cart for non-SSL products

`GET /execute/Market/create_shopping_cart_non_ssl` · RW · rollback: none · since cPanel 62

This function creates a shopping cart for non-SSL products. It validates the access token, retrieves product information, creates a shopping cart with the provider, and returns the order details and checkout URL.

**Parameters**

- `access_token` · **required** · string <uuid> · e.g. `1a676e6f-99fc-11e6-9ab6-e60a769b73bc` — The access token obtained during login to the cPanel Market provider.
- `product_name` · **required** · string · e.g. `cpanel-ssl` — The name of the product to purchase.
- `url_after_checkout` · **required** · string <url> · e.g. `http://www.example.com/thenextplace` — The URL to which the provider redirects the user after the checkout process is complete.
- `domain` · optional · string · e.g. `example.com` — The domain associated with the product purchase. This parameter is optional.

**Returns** `data`: object

- `checkout_url` (string <url>) — The URL of the provider's checkout page.
- `order_id` (string) — The order ID assigned by the provider.
- `order_items_ref` (array of object) — An array of objects that contain information about the items in the shopping cart.

```bash
uapi --output=jsonpretty \
  --user=username \
  Market \
  create_shopping_cart_non_ssl \
  access_token='1a676e6f-99fc-11e6-9ab6-e60a769b73bc' \
  product_name='cpanel-ssl' \
  url_after_checkout='http://www.example.com/thenextplace'
```

<a id="market-get-all-products"></a>
### `Market::get_all_products` — Return provider's available products

`GET /execute/Market/get_all_products` · RO · rollback: none · since cPanel 56

This function lists all products available through all enabled cPanel Market providers.

**Returns** `data`: array of object

- *(array of objects)*
  - *variant: object*
    - `base_name` (string) — The provider's base name.
    - `billing_type` (string) — The provider's billing type
    - `description` (string) — The product's description.
    - `display_name` (string) — The product's display name.
    - `enabled` (integer (`0`, `1`)) — Whether the product is enabled in the cPanel Market.; `1` - Enabled.; `0` - Not enabled.
    - `icon` (string <base64 image>) — The product's display icon.
    - `icon_mime_type` (string <MIME>) — The icon's file type.
    - `license_term` (integer) — The providers license term
    - `max_users` (integer) — The maximum number of users.
    - `maximum_server_price` (number <currency>) — The maximum price that the system will allow for the product.
    - `minimum_server_price` (number <currency>) — The minimum price that the system will allow for the product.
    - `price` (number <currency>) — The product's price.
    - `price_unit` (string <ISO-4217>) — The currency code of the product's price.
    - `product` (string) — The product name.
    - `product_category` (string) — The product's category.
    - `product_group` (string) — The product's group.
    - `product_id` (integer) — The product's ID.
    - `provider_display_name` (string) — The cPanel Market provider's display name.
    - `provider_name` (string) — The cPanel Market provider's name.
    - `recommended` (integer (`0`, `1`)) — Whether the product is recommended.; `1` — We recommend the product.; `0` — We do not recommend the product.
    - `requires_ip` (integer (`0`, `1`)) — Whether the product requires an IP address.; `1` — Requires an IP.; `0` — Does **not** require an IP.
  - *variant: object*
    - `base_name` (string) — The provider's base name.
    - `billing_type` (string) — The provider's billing type
    - `description` (string) — The product's description.
    - `display_name` (string) — The product's display name.
    - `enabled` (integer (`0`, `1`)) — Whether the product is enabled in the cPanel Market.; `1` - Enabled.; `0` - Not enabled.
    - `icon` (string <base64 image>) — The product's display icon.
    - `icon_mime_type` (string <MIME>) — The icon's file type.
    - `license_term` (integer) — The providers license term
    - `max_users` (integer) — The maximum number of users.
    - `maximum_server_price` (number <currency>) — The maximum price that the system will allow for the product.
    - `minimum_server_price` (number <currency>) — The minimum price that the system will allow for the product.
    - `price` (number <currency>) — The product's price.
    - `price_unit` (string <ISO-4217>) — The currency code of the product's price.
    - `product` (string) — The product name.
    - `product_category` (string) — The product's category.
    - `product_group` (string) — The product's group.
- … (truncated; see the online reference)

```bash
uapi --output=jsonpretty \
  --user=username \
  Market \
  get_all_products
```

<a id="market-get-build-cart-url"></a>
### `Market::get_build_cart_url` — Build cart URL for a product

`GET /execute/Market/get_build_cart_url` · RW · rollback: none · since cPanel 62

This function builds the URL for the shopping cart page for the specified product. The system saves session data and constructs a full cPanel URL pointing to the product purchase page.

**Parameters**

- `product_name` · **required** · string · e.g. `cpanel-ssl` — The name of the product for which to build the cart URL.
- `domain` · optional · string · e.g. `example.com` — The domain associated with the product purchase. This parameter is optional.

**Returns** `data`: object

- `url` (string <url>) — The full cPanel URL for the product purchase cart page, including the security token.

```bash
uapi --output=jsonpretty \
  --user=username \
  Market \
  get_build_cart_url \
  product_name='cpanel-ssl' \
  domain='example.com'
```

<a id="market-get-completion-url"></a>
### `Market::get_completion_url` — Get product purchase completion URL

`GET /execute/Market/get_completion_url` · RO · since cPanel 62

This function builds the full cPanel URL for the product purchase completion page. The URL includes the security token and points to the completion page for the specified product.

**Parameters**

- `product_name` · **required** · string · e.g. `cpanel-ssl` — The name of the product for which to retrieve the completion URL.

**Returns** `data`: object

- `completion_url` (string <url>) — The full cPanel URL for the product purchase completion page, including the security token.

```bash
uapi --output=jsonpretty \
  --user=username \
  Market \
  get_completion_url \
  product_name='cpanel-ssl'
```

<a id="market-get-license-info"></a>
### `Market::get_license_info` — Retrieve license information for a domain

`GET /execute/Market/get_license_info` · RW · rollback: none · since cPanel 62

This function retrieves license information for the specified domain from the cPanel Store and saves it to the current session.

**Parameters**

- `domain` · optional · string · e.g. `example.com` — The domain for which to retrieve license information. This parameter is optional.

**Returns** `data`: object — This function does not return data.

```bash
uapi --output=jsonpretty \
  --user=username \
  Market \
  get_license_info \
  domain='example.com'
```

<a id="market-get-login-url"></a>
### `Market::get_login_url` — Return provider's login URL

`GET /execute/Market/get_login_url` · RO · since cPanel 56

This function retrieves the login URL for the cPanel Market provider.

**Parameters**

- `provider` · **required** · string · e.g. `cPStore` — The cPanel Market provider's name.
- `url_after_login` · **required** · string <url> · e.g. `http://hostname.example.com/redirectionlocation.cgi?state` — Where the cPanel Market provider redirects the user's browser after they log in.

**Returns** `data`: string <url> — The URL to which to redirect the browser after login.

```bash
uapi --output=jsonpretty \
  --user=username \
  Market \
  get_login_url \
  provider='cPStore' \
  url_after_login='http://hostname.example.com/redirectionlocation.cgi?state'
```

<a id="market-get-product-info"></a>
### `Market::get_product_info` — Retrieve product information

`GET /execute/Market/get_product_info` · RO · since cPanel 62

This function retrieves product information for the specified product name, including the product ID, redirect path, and redirect URLs for successful and failed purchases.

**Parameters**

- `product_name` · **required** · string · e.g. `cpanel-ssl` — The name of the product for which to retrieve information.

**Returns** `data`: object

- `product_id` (string) — The product's identifier in the cPanel Store.
- `redirect_path` (string) — The cPanel path to redirect to after a purchase attempt.
- `redirect_url_failure` (string <url>) — The full cPanel URL to redirect to after a failed purchase, including the security token and relevant query string parameters.
- `redirect_url_success` (string <url>) — The full cPanel URL to redirect to after a successful purchase, including the security token and relevant query string parameters.

```bash
uapi --output=jsonpretty \
  --user=username \
  Market \
  get_product_info \
  product_name='cpanel-ssl'
```

<a id="market-get-providers-list"></a>
### `Market::get_providers_list` — Return enabled providers

`GET /execute/Market/get_providers_list` · RO · since cPanel 56

This function lists the names of enabled cPanel Market providers.

**Returns** `data`: array of object — An array of objects that lists enabled providers in the cPanel Market.

- *(array of objects)*
  - `display_name` (string) — The cPanel Market provider's display name.
  - `name` (string) — The cPanel Market provider's name.

```bash
uapi --output=jsonpretty \
  --user=username \
  Market \
  get_providers_list
```

<a id="market-set-status-of-pending-queue-items"></a>
### `Market::set_status_of_pending_queue_items` — Update status of items in pending queue

`GET /execute/Market/set_status_of_pending_queue_items` · RW · rollback: none · since cPanel 56

This function sets the status of an item or items in the cPanel Market pending queue.

**Parameters**

- `order_item_id` · **required** · string — The ID of the ordered item. Note: To set the status for multiple items, duplicate or increment the parameter name. For example, to change the status for three certificates, use the `order_item_id` parameter multiple times or use the `order_item_id-1`, `order_item_id-2`, and `order_item_id-3` parameters.
- `provider` · **required** · string · e.g. `cPStore` — The cPanel Market provider's name.
- `status` · **required** · string (`confirmed`) · e.g. `confirmed` — The new status of the item in the cPanel Market pending queue.; `confirmed` — The system confirmed payment for the item with the provider.

**Returns** `data`: object — The function only returns these values if the user or users do **not** have the `order_item_id` item in the cPanel Market pending queue.

- `error_type` (string (`EntryDoesNotExist`)) — The type of error that the function encountered.; `EntryDoesNotExist` — The returned `order_item_ids` do not exist in the cPanel Market pending queue for the user.
- `order_item_ids` (array of integer) — An array that lists order item IDs which do not exist in the cPanel Market pending queue for the user.

```bash
uapi --output=jsonpretty \
  --user=username \
  Market \
  set_status_of_pending_queue_items \
  provider='cPStore' \
  order_item_id='12345' \
  status='confirmed'
```

<a id="market-set-url-after-checkout"></a>
### `Market::set_url_after_checkout` — Update URL after checkout

`GET /execute/Market/set_url_after_checkout` · RW · rollback: none · since cPanel 56

This function updates the URL to which a provider sends a user after they check out.

**Parameters**

- `access_token` · **required** · string · e.g. `725431a1-d5bc-11e5-a28b-8b0e09a93f05` — The access token for the session to the cPanel Market provider.
- `order_id` · **required** · integer · e.g. `123456` — The order ID that the cPanel Market provider assigned.
- `provider` · **required** · string · e.g. `cPStore` — The cPanel Market provider's name.
- `url_after_checkout` · **required** · string <url> · e.g. `http://checkout.example.com` — The URL to send the browser after the user checks out.

**Returns** `data`: object

- `error_type` (string) — Any errors that the function encounters.

```bash
uapi --output=jsonpretty \
  --user=username \
  Market \
  set_url_after_checkout \
  provider='cPStore' \
  access_token='725431a1-d5bc-11e5-a28b-8b0e09a93f05' \
  order_id='123456' \
  url_after_checkout='http://checkout.example.com'
```

<a id="market-validate-login-token"></a>
### `Market::validate_login_token` — Validate login token

`GET /execute/Market/validate_login_token` · RW · rollback: none · since cPanel 56

This function validates a login token to a cPanel Market provider and returns an access token.

**Parameters**

- `login_token` · **required** · string · e.g. `8675309` — The login token for the cPanel Market provider.
- `provider` · **required** · string · e.g. `cPStore` — The name of the cPanel Market provider.
- `url_after_login` · **required** · string <url> · e.g. `http://hostname.example.com/redirectionlocation.cgi?state` — The `url_after_login` value that you sent to UAPI's `Market::get_login_url` function.

**Returns** `data`: object

- `access_token` (string) — The access token that returns from the code parameter after you log in.

```bash
uapi --output=jsonpretty \
  --user=username \
  Market \
  validate_login_token \
  provider='cPStore' \
  login_token='8675309' \
  url_after_login='http://hostname.example.com/redirectionlocation.cgi?state'
```

