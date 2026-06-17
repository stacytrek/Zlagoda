-- 1. Стартові працівники
INSERT INTO Employee (id_employee, empl_surname, empl_name, empl_patronymic, empl_role, salary, date_of_birth, date_of_start, phone_number, city, street, zip_code, password_hash) 
VALUES 
('M001', 'Петренко', 'Володимир', 'None', 'Менеджер', 25000, '2005-01-01', '2026-01-01', '+380990000001', 'Київ', 'вул. Сковороди', '04070', '{MANAGER_HASH}'),
('K001', 'Шевченко', 'Валентина', 'None', 'Касир', 15000, '2005-02-02', '2026-01-01', '+380990000002', 'Київ', 'вул. Софіївська', '04070', '{CASHIER_HASH}');

-- 2. Базове наповнення системи
INSERT INTO Category (category_name) VALUES ('Випічка');
INSERT INTO Product (category_number, product_name, characteristics) VALUES (1, 'Булочка з корицею', 'Свіжа, ароматна');
INSERT INTO Store_Product (UPC, id_product, selling_price, products_number, promotional_product) VALUES ('112233445577', 1, 35.00, 100, 0);
INSERT INTO Customer_Card (card_number, cust_surname, cust_name, phone_number, city, street, zip_code, percent) VALUES ('C000000000001', 'Шевченко', 'Тарас', '+380991112233', 'Київ', 'вул. Хрещатик', '01001', 5);

-- 3. Стартові чеки
INSERT INTO Receipt (check_number, id_employee, card_number, print_date, sum_total, vat) VALUES ('R000000001', 'K001', 'C000000000001', '2026-06-16 10:00:00', 35.00, 7.00);
INSERT INTO Sale (UPC, check_number, product_number, selling_price) VALUES ('112233445577', 'R000000001', 1, 35.00);

INSERT INTO Receipt (check_number, id_employee, print_date, sum_total, vat) VALUES ('R000000002', 'K001', '2026-06-16 11:30:00', 70.00, 14.00);
INSERT INTO Sale (UPC, check_number, product_number, selling_price) VALUES ('112233445577', 'R000000002', 2, 35.00);