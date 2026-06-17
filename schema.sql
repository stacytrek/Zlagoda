-- 1. СТРУКТУРА ТАБЛИЦЬ
CREATE TABLE IF NOT EXISTS Employee (
    id_employee VARCHAR(10) PRIMARY KEY,
    empl_surname VARCHAR(50) NOT NULL,
    empl_name VARCHAR(50) NOT NULL,
    empl_patronymic VARCHAR(50),
    empl_role VARCHAR(10) NOT NULL,
    salary DECIMAL(13,4) NOT NULL,
    date_of_birth DATE NOT NULL,
    date_of_start DATE NOT NULL,
    phone_number VARCHAR(13) NOT NULL,
    city VARCHAR(50) NOT NULL,
    street VARCHAR(50) NOT NULL,
    zip_code VARCHAR(9) NOT NULL,
    password_hash VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS Category (
    category_number INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS Product (
    id_product INTEGER PRIMARY KEY AUTOINCREMENT,
    category_number INTEGER NOT NULL,
    product_name VARCHAR(50) NOT NULL,
    characteristics VARCHAR(100) NOT NULL,
    FOREIGN KEY (category_number) REFERENCES Category(category_number)
);

CREATE TABLE IF NOT EXISTS Store_Product (
    UPC VARCHAR(12) PRIMARY KEY,
    UPC_prom VARCHAR(12),
    id_product INTEGER NOT NULL,
    selling_price DECIMAL(13,4) NOT NULL,
    products_number INTEGER NOT NULL,
    promotional_product INTEGER NOT NULL,
    FOREIGN KEY (id_product) REFERENCES Product(id_product),
    FOREIGN KEY (UPC_prom) REFERENCES Store_Product(UPC)
);

CREATE TABLE IF NOT EXISTS Customer_Card (
    card_number VARCHAR(13) PRIMARY KEY,
    cust_surname VARCHAR(50) NOT NULL,
    cust_name VARCHAR(50) NOT NULL,
    cust_patronymic VARCHAR(50),
    phone_number VARCHAR(13) NOT NULL,
    city VARCHAR(50),
    street VARCHAR(50),
    zip_code VARCHAR(9),
    percent INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS Receipt (
    check_number VARCHAR(10) PRIMARY KEY,
    id_employee VARCHAR(10) NOT NULL,
    card_number VARCHAR(13),
    print_date DATETIME NOT NULL,
    sum_total DECIMAL(13,4) NOT NULL,
    vat DECIMAL(13,4) NOT NULL,
    FOREIGN KEY (id_employee) REFERENCES Employee(id_employee),
    FOREIGN KEY (card_number) REFERENCES Customer_Card(card_number)
);

CREATE TABLE IF NOT EXISTS Sale (
    UPC VARCHAR(12) NOT NULL,
    check_number VARCHAR(10) NOT NULL,
    product_number INTEGER NOT NULL,
    selling_price DECIMAL(13,4) NOT NULL,
    PRIMARY KEY (UPC, check_number),
    FOREIGN KEY (UPC) REFERENCES Store_Product(UPC),
    FOREIGN KEY (check_number) REFERENCES Receipt(check_number)
);