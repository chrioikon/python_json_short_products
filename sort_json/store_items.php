<?php
require __DIR__ . '/common.php';

// Products sheet columns passed to sort_json.py.
const SORT_COLUMNS = 'ItemCode=2 ItemPrice=9 TreatmentGroup=1 DoseFamily=1 Type=1 ItemName=3 HebrewName=4 HebrewBrand=5';

// Request field => [sort_json.py option, allowed extensions, required].
const SORT_FILES = [
    'Products file' => ['-f', ['ods'], true],
    'Items file' => ['-i', ['csv'], true],
    'Rules file' => ['-r', ['json'], false],
    'Output json file' => ['-s', ['json'], false],
];

const BACKUP_DIR = DATA_DIR . 'backup/';
const BACKUP_MIN_COUNT = 10;   // start pruning when a file has this many backups
const BACKUP_MAX_DELETE = 6;   // delete at most this many per run
const BACKUP_MIN_AGE_DAYS = 5; // only delete backups at least this old

// Save the edited items table as CSV (with a blank line after every row, as sort_json.py expects).
function store_items($rows, $items_file)
{
    $path = data_path($items_file, ['csv']);
    if ($path === false || !is_array($rows) || ($handle = fopen($path, 'w')) === false) {
        fail(400, 'Invalid items file.');
    }
    $header = false;
    foreach ($rows as $row) {
        if (empty($header)) {
            $header = array_keys($row);
            fputcsv($handle, $header);
            fputs($handle, "\n");
            $header = array_flip($header);
        }
        if (!empty($row['ItemCode'])) {
            fputcsv($handle, array_merge($header, $row));
            fputs($handle, "\n");
        }
    }
    fclose($handle);
}

// Run sort_json.py with the files named in $info and echo its output.
function sort_json($info)
{
    $command = './sort_json.py ' . SORT_COLUMNS;
    foreach (SORT_FILES as $field => list($option, $extensions, $required)) {
        if (empty($info[$field])) {
            if ($required) {
                fail(400, "Missing $field.");
            }
            continue;
        }
        if (data_path($info[$field], $extensions) === false) {
            fail(400, "Invalid $field. Please try again.");
        }
        $command .= " $option " . shell_quote($info[$field]);
    }

    exec($command . ' 2>&1', $lines, $status);
    $output = implode("\n", $lines);
    if ($status !== 0) {
        fail(preg_match('/Please\s+try\s+again/', $output) ? 400 : 500, $output);
    }
    echo $output;
}

// Back up every data file (once a day) and prune old backups. Products sheets are removed after backup.
function backup_data_files()
{
    if (!file_exists(BACKUP_DIR)) {
        mkdir(BACKUP_DIR, 0755, true);
    }
    $backups = scandir(BACKUP_DIR);
    $now = new DateTime('now');

    foreach (preg_grep('/(\.csv$)|(\.json$)|(\.ods$)/', scandir(DATA_DIR)) as $file) {
        if (copy(DATA_DIR . $file, BACKUP_DIR . date('Y-m-d') . '.' . $file) && preg_match('/\.ods$/', $file)) {
            unlink(DATA_DIR . $file);
        }

        $file_backups = array_filter($backups, function ($backup) use ($file) {
            return strpos($backup, $file) !== false;
        });
        if (count($file_backups) < BACKUP_MIN_COUNT) {
            continue;
        }
        $deleted = 0;
        foreach ($file_backups as $backup) {
            if ($deleted >= BACKUP_MAX_DELETE || !preg_match('/^\d+-\d+-\d+/', $backup, $date)) {
                continue;
            }
            if (intval((new DateTime($date[0]))->diff($now)->format('%a')) >= BACKUP_MIN_AGE_DAYS) {
                unlink(BACKUP_DIR . $backup);
                $deleted++;
            }
        }
    }
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $post = json_decode(file_get_contents('php://input'), true);
    if (isset($post['jsonData'])) {
        store_items($post['jsonData'], isset($post['Items']) ? $post['Items'] : '');
    } elseif (isset($post['info'])) {
        sort_json($post['info']);
    } else {
        fail(400);
    }
} elseif ($_SERVER['REQUEST_METHOD'] === 'GET') {
    backup_data_files();
}
