<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $post = json_decode(file_get_contents('php://input'), true);
    if (isset($post['jsonData'])) {
        $jsonData = $post['jsonData'];
        $itemsFile = $post['Items'];
        if (preg_match('/.+\.csv/', $itemsFile) >= 1) {
            if (($handle = fopen("./data/" . $itemsFile, "w")) !== FALSE) {
                $header = false;
                foreach ($jsonData as $single_json) {
                    if (empty($header)) {
                        $header = array_keys($single_json);
                        fputcsv($handle, $header);
                        fputs($handle, "\n");
                        $header = array_flip($header);
                    }
                    if (!empty($single_json["ItemCode"])) {
                        fputcsv($handle, array_merge($header, $single_json));
                        fputs($handle, "\n");
                    }
                }
            }
        }
    } else if (isset($post['info'])) {

        if (!(isset($post['info']['Products file'])) && (isset($post['info']['Items file']))) {
            http_response_code(400);
            exit(1);
        }
        
        $output = "";
        if ((isset($post['info']['Rules file'])) && (isset($post['info']['Output json file']))) {

           echo $output = shell_exec("./sort_json.py ItemCode=2 ItemPrice=9 TreatmentGroup=1  DoseFamily=1 Type=1 ItemName=3 HebrewName=4 HebrewBrand=5 -f " . preg_replace('/\)/', '\\)', preg_replace('/\(/', '\\(', preg_replace('/\s+/', '\\ ', $post['info']['Products file']))) . " -i " . preg_replace('/\)/', '\\)', preg_replace('/\(/', '\\(', preg_replace('/\s+/', '\\ ', $post['info']['Items file']))) . " -r " . preg_replace('/\)/', '\\)', preg_replace('/\(/', '\\(', preg_replace('/\s+/', '\\ ', $post['info']['Rules file']))) . " -s " . preg_replace('/\)/', '\\)', preg_replace('/\(/', '\\(', preg_replace('/\s+/', '\\ ', $post['info']['Output json file']))) . "  2>&1");
        } else if ((isset($post['info']['Rules file']))) {

          echo  $output = shell_exec("./sort_json.py ItemCode=2 ItemPrice=9 TreatmentGroup=1  DoseFamily=1 Type=1 ItemName=3 HebrewName=4 HebrewBrand=5 -f " . preg_replace('/\)/', '\\)', preg_replace('/\(/', '\\(', preg_replace('/\s+/', '\\ ', $post['info']['Products file']))) . " -i " . preg_replace('/\)/', '\\)', preg_replace('/\(/', '\\(', preg_replace('/\s+/', '\\ ', $post['info']['Items file']))) . " -r " . preg_replace('/\)/', '\\)', preg_replace('/\(/', '\\(', preg_replace('/\s+/', '\\ ', $post['info']['Rules file']))) . "   2>&1");
        } else if (isset($post['info']['Output json file'])) {

          echo  $output = shell_exec("./sort_json.py ItemCode=2 ItemPrice=9 TreatmentGroup=1  DoseFamily=1 Type=1 ItemName=3 HebrewName=4 HebrewBrand=5 -f " . preg_replace('/\)/', '\\)', preg_replace('/\(/', '\\(', preg_replace('/\s+/', '\\ ', $post['info']['Products file']))) . " -i " . preg_replace('/\)/', '\\)', preg_replace('/\(/', '\\(', preg_replace('/\s+/', '\\ ', $post['info']['Items file']))) . " -s " . preg_replace('/\)/', '\\)', preg_replace('/\(/', '\\(', preg_replace('/\s+/', '\\ ', $post['info']['Output json file']))) . "   2>&1");
        } else {


         echo   $output = shell_exec("./sort_json.py ItemCode=2 ItemPrice=9 TreatmentGroup=1  DoseFamily=1 Type=1 ItemName=3 HebrewName=4 HebrewBrand=5 -f " . preg_replace('/\)/', '\\)', preg_replace('/\(/', '\\(', preg_replace('/\s+/', '\\ ', $post['info']['Products file']))) . " -i " . preg_replace('/\)/', '\\)', preg_replace('/\(/', '\\(', preg_replace('/\s+/', '\\ ', $post['info']['Items file']))) . " 2>&1");
        }

        if (preg_match('/Please\s+try\s+again/', $output) >= 1) {
            http_response_code(400);
            exit(1);
        }
    }
} else if ($_SERVER["REQUEST_METHOD"] == "GET") {

    if (!file_exists('./data/backup/')) {
        mkdir('./data/backup/', 0755, true);
    }
    $backupList = scandir('./data/backup/');
    $fileList = preg_grep("/(\.csv$)|(\.json$)|(\.ods$)/",scandir("./data"));

    foreach ($fileList as $file_info) {
        if (($handle = fopen("./data/" . $file_info, "r")) !== FALSE) {
            $b_handle = fopen("./data/backup/" . date('Y-m-d') . "." . $file_info, "w");
            while (!feof($handle)) {
                fwrite($b_handle, fgets($handle));
            }
            fclose($b_handle);
            fclose($handle);
            if (preg_match('/\.ods$/',$file_info)) {
                unlink("./data/".$file_info);
            }
        }
        $count = 0;
        $corrFiles = array();
        foreach ($backupList as $file) {

            if (strpos($file, $file_info) !== false) {
                array_push($corrFiles, $file);
                $count++;
            }
        }


        if ($count >= 10) {
            $thres = 5;
            foreach ($corrFiles as $corrFile) {
                preg_match("/^(\d+)-(\d+)-(\d+)/", $corrFile, $m);
                $da = new DateTime($m[0]);
                $daNow = new DateTime('now');
                $interval = $da->diff($daNow);
                if (intval($interval->format("%a")) >= 5 && $thres >= 0) {
                    unlink('./data/backup/' . $corrFile);
                    $thres--;
                }
            }
        }
    }
}
