// ==========================================
// SMARTCANTEEN CART SYSTEM
// CUSTOMER VERSION
// FLASK DATABASE CONNECTED
// PAYMENT METHOD CONNECTED
// ==========================================


// ==========================================
// ADD FOOD TO CART
// ==========================================

function addFood(name, price) {

    let cart =
        JSON.parse(localStorage.getItem("cart")) || [];


    let existingFood =
        cart.find(function(item) {

            return item.name === name;

        });


    if (existingFood) {

        existingFood.quantity += 1;

    } else {

        cart.push({

            name: name,

            price: Number(price),

            quantity: 1

        });

    }


    localStorage.setItem(
        "cart",
        JSON.stringify(cart)
    );


    updateCartCount();


    alert(
        "✅ " +
        name +
        " added to cart!"
    );

}


// ==========================================
// UPDATE CART COUNT
// ==========================================

function updateCartCount() {

    let cart =
        JSON.parse(localStorage.getItem("cart")) || [];


    let count = 0;


    cart.forEach(function(item) {

        count += Number(
            item.quantity
        );

    });


    let cartLink =
        document.getElementById(
            "cart-link"
        );


    if (cartLink) {

        if (count > 0) {

            cartLink.innerHTML =
                "🛒 Cart (" +
                count +
                ")";

        } else {

            cartLink.innerHTML =
                "🛒 Cart";

        }

    }

}


// ==========================================
// UPDATE LOGIN NAVBAR
// ==========================================

function updateLoginNavbar() {

    let loginLinks =
        document.querySelectorAll(
            ".login-btn"
        );


    let loggedIn =
        localStorage.getItem(
            "loggedIn"
        );


    let userEmail =
        localStorage.getItem(
            "userEmail"
        );


    loginLinks.forEach(function(link) {

        if (
            loggedIn === "true"
            &&
            userEmail
        ) {

            link.innerHTML =
                "👤 " +
                userEmail +
                " | Logout";


            link.href = "#";


            link.onclick =
                function(event) {

                    event.preventDefault();

                    logoutUser();

                };


        } else {

            link.innerHTML =
                "🔐 Login";


            link.href =
                "/login";


            link.onclick = null;

        }

    });

}


// ==========================================
// LOGOUT
// ==========================================

function logoutUser() {

    localStorage.removeItem(
        "loggedIn"
    );


    localStorage.removeItem(
        "userEmail"
    );


    alert(
        "👋 You have been logged out."
    );


    window.location.href =
        "/";

}


// ==========================================
// LOAD CART
// ==========================================

function loadCart() {

    let cart =
        JSON.parse(
            localStorage.getItem("cart")
        ) || [];


    let container =
        document.getElementById(
            "cart-container"
        );


    let emptyCart =
        document.getElementById(
            "empty-cart"
        );


    let summary =
        document.getElementById(
            "cart-summary"
        );


    if (!container) {

        return;

    }


    container.innerHTML = "";


    // ======================================
    // EMPTY CART
    // ======================================

    if (cart.length === 0) {

        if (emptyCart) {

            emptyCart.style.display =
                "block";

        }


        if (summary) {

            summary.style.display =
                "none";

        }


        return;

    }


    // ======================================
    // CART HAS ITEMS
    // ======================================

    if (emptyCart) {

        emptyCart.style.display =
            "none";

    }


    if (summary) {

        summary.style.display =
            "block";

    }


    let subtotal = 0;


    cart.forEach(
        function(item, index) {

            let price =
                Number(item.price);


            let quantity =
                Number(item.quantity);


            let itemTotal =
                price * quantity;


            subtotal +=
                itemTotal;


            let cartItem =
                document.createElement(
                    "div"
                );


            cartItem.style.cssText = `

                max-width:700px;

                margin:15px auto;

                padding:20px;

                background:white;

                border-radius:15px;

                box-shadow:
                    0 5px 20px
                    rgba(20,30,50,0.07);

                display:flex;

                justify-content:space-between;

                align-items:center;

                gap:15px;

            `;


            cartItem.innerHTML = `

                <div>

                    <h3>
                        ${item.name}
                    </h3>

                    <p
                        style="
                            color:#667085;
                        "
                    >
                        ₹${price}
                        ×
                        ${quantity}
                    </p>

                </div>


                <div
                    style="
                        text-align:right;
                    "
                >

                    <strong
                        style="
                            font-size:18px;
                        "
                    >
                        ₹${itemTotal}
                    </strong>


                    <br><br>


                    <button

                        type="button"

                        onclick="
                            removeItem(${index})
                        "

                        style="
                            border:none;
                            background:#fee2e2;
                            color:#dc2626;
                            padding:7px 12px;
                            border-radius:7px;
                            cursor:pointer;
                            font-weight:600;
                        "

                    >

                        Remove

                    </button>

                </div>

            `;


            container.appendChild(
                cartItem
            );

        }
    );


    // ======================================
    // TOTAL
    // ======================================

    let platformFee = 10;


    let total =
        subtotal +
        platformFee;


    let subtotalElement =
        document.getElementById(
            "subtotal"
        );


    let totalElement =
        document.getElementById(
            "total"
        );


    if (subtotalElement) {

        subtotalElement.innerText =
            "₹" +
            subtotal;

    }


    if (totalElement) {

        totalElement.innerText =
            "₹" +
            total;

    }

}


// ==========================================
// REMOVE ITEM
// ==========================================

function removeItem(index) {

    let cart =
        JSON.parse(
            localStorage.getItem("cart")
        ) || [];


    cart.splice(
        index,
        1
    );


    localStorage.setItem(
        "cart",
        JSON.stringify(cart)
    );


    loadCart();


    updateCartCount();

}


// ==========================================
// GET PAYMENT METHOD
// ==========================================

function getPaymentMethod() {

    let selected =
        document.querySelector(
            'input[name="payment_method"]:checked'
        );


    if (selected) {

        return selected.value;

    }


    return "Cash on Pickup";

}


// ==========================================
// PLACE ORDER
// ==========================================

async function placeOrder() {

    let cart =
        JSON.parse(
            localStorage.getItem("cart")
        ) || [];


    // ======================================
    // CHECK CART
    // ======================================

    if (cart.length === 0) {

        alert(
            "⚠️ Your cart is empty!"
        );

        return;

    }


    // ======================================
    // GET PAYMENT METHOD
    // ======================================

    let paymentMethod =
        getPaymentMethod();


    // ======================================
    // CALCULATE SUBTOTAL
    // ======================================

    let subtotal = 0;


    cart.forEach(
        function(item) {

            let price =
                Number(item.price);


            let quantity =
                Number(item.quantity);


            subtotal +=
                price *
                quantity;

        }
    );


    // ======================================
    // PLATFORM FEE
    // ======================================

    let platformFee = 10;


    // ======================================
    // FINAL TOTAL
    // ======================================

    let total =
        subtotal +
        platformFee;


    // ======================================
    // CUSTOMER INFORMATION
    // ======================================

    let customerName =
        localStorage.getItem(
            "customerName"
        )
        ||
        localStorage.getItem(
            "userEmail"
        )
        ||
        "Guest";


    // ======================================
    // PREPARE ITEMS
    // ======================================

    let itemsForDatabase =
        JSON.stringify(
            cart
        );


    // ======================================
    // SEND TO FLASK
    // ======================================

    try {

        let response =
            await fetch(
                "/api/orders",
                {

                    method:
                        "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify({

                            customer_name:
                                customerName,

                            items:
                                itemsForDatabase,

                            total:
                                total,

                            payment_method:
                                paymentMethod

                        })

                }
            );


        // ==================================
        // CHECK HTTP RESPONSE
        // ==================================

        if (!response.ok) {

            let errorText =
                await response.text();


            console.error(
                "Server Error:",
                response.status,
                errorText
            );


            alert(
                "❌ Order failed.\n\n" +
                "Server error: " +
                response.status
            );


            return;

        }


        // ==================================
        // READ JSON RESPONSE
        // ==================================

        let result;


        try {

            result =
                await response.json();

        } catch (jsonError) {

            console.error(
                "Invalid JSON response:",
                jsonError
            );


            alert(
                "❌ Invalid server response.\n\n" +
                "Please check Flask server."
            );


            return;

        }


        console.log(
            "Order Response:",
            result
        );


        // ==================================
        // CHECK SUCCESS
        // ==================================

        if (!result.success) {

            alert(
                "❌ Order could not be placed.\n\n" +
                (
                    result.message
                    ||
                    "Unknown error"
                )
            );


            return;

        }


        // ==================================
        // ORDER ID
        // ==================================

        let orderId =
            result.order_id;


        // ==================================
        // PAYMENT METHOD FROM SERVER
        // ==================================

        let savedPaymentMethod =
            result.payment_method
            ||
            paymentMethod
            ||
            "Cash on Pickup";


        // ==================================
        // CREATE LOCAL ORDER
        // ==================================

        let newOrder = {

            orderId:
                orderId,

            databaseId:
                result.database_id,

            items:
                cart,

            subtotal:
                subtotal,

            platformFee:
                platformFee,

            total:
                total,

            paymentMethod:
                savedPaymentMethod,

            status:
                "Confirmed",

            trackingStage:
                2,

            trackingStatus:
                "Confirmed",

            trackingMessage:
                "Your order is confirmed and being processed.",

            restaurant:
                "KK Foods",

            estimatedTime:
                "15–20 minutes"

        };


        // ==================================
        // SAVE ORDER HISTORY
        // ==================================

        let orders =
            JSON.parse(
                localStorage.getItem(
                    "orders"
                )
            ) || [];


        orders.unshift(
            newOrder
        );


        localStorage.setItem(
            "orders",
            JSON.stringify(
                orders
            )
        );


        // ==================================
        // SAVE LAST ORDER
        // ==================================

        localStorage.setItem(
            "lastOrderId",
            orderId
        );


        // ==================================
        // CLEAR CART
        // ==================================

        localStorage.removeItem(
            "cart"
        );


        updateCartCount();


        // ==================================
        // SUCCESS
        // ==================================

        alert(

            "✅ Order placed successfully!\n\n" +

            "Order ID: " +
            orderId +

            "\n\n" +

            "Payment: " +
            savedPaymentMethod

        );


        // ==================================
        // GO TO SUCCESS PAGE
        // ==================================

        window.location.href =
            "/order-success";


    } catch (error) {

        console.error(
            "Order Error:",
            error
        );


        alert(
            "❌ Cannot connect to SmartCanteen server.\n\n" +
            "Please make sure Flask is running."
        );

    }

}


// ==========================================
// PAGE LOAD
// ==========================================

document.addEventListener(
    "DOMContentLoaded",
    function() {

        updateCartCount();

        loadCart();

        updateLoginNavbar();

    }
);