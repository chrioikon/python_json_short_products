<?php
require __DIR__ . '/common.php';

// Return the rows of an items CSV file as a JSON array of objects.
if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    fail(405);
}
$path = data_path(isset($_GET['Items']) ? $_GET['Items'] : '', ['csv']);
if ($path === false || !is_file($path) || ($handle = fopen($path, 'r')) === false) {
    fail(404, 'Items file not found.');
}

$column_names = fgetcsv($handle);
$rows = [];
while (($csv = fgetcsv($handle)) !== false) {
    if ($csv === [null]) {
        continue; // blank line
    }
    $row = [];
    foreach ($column_names as $index => $column_name) {
        $row[$column_name] = isset($csv[$index]) ? $csv[$index] : '';
    }
    $rows[] = $row;
}
fclose($handle);

header('Content-Type: application/json; charset=utf-8');
echo json_encode($rows);
