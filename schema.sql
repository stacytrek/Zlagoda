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

-- 2. НАПОВНЕННЯ: 1 КАТЕГОРІЯ, 1 ТОВАР, 1 КЛІЄНТ, 2 ЧЕКИ
INSERT INTO Category (category_name) VALUES ('Випічка');
INSERT INTO Product (category_number, product_name, characteristics) VALUES (1, 'Булочка з корицею', 'Свіжа, ароматна');
INSERT INTO Store_Product (UPC, id_product, selling_price, products_number, promotional_product)
VALUES ('112233445577', 1, 35.00, 100, 0);

INSERT INTO Customer_Card (card_number, cust_surname, cust_name, phone_number, city, street, zip_code, percent)
VALUES ('C000000000001', 'Шевченко', 'Тарас', '+380991112233', 'Київ', 'вул. Хрещатик', '01001', 5);

INSERT INTO Receipt (check_number, id_employee, card_number, print_date, sum_total, vat)
VALUES ('R000000001', 'K001', 'C000000000001', '2026-06-16 10:00:00', 35.00, 7.00);
INSERT INTO Sale (UPC, check_number, product_number, selling_price)
VALUES ('112233445577', 'R000000001', 1, 35.00);

INSERT INTO Receipt (check_number, id_employee, print_date, sum_total, vat)
VALUES ('R000000002', 'K001', '2026-06-16 11:30:00', 70.00, 14.00);
INSERT INTO Sale (UPC, check_number, product_number, selling_price)
VALUES ('112233445577', 'R000000002', 2, 35.00);