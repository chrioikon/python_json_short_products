<?php
if ($_SERVER['REQUEST_METHOD'] === 'GET'){
    if (preg_match('/.+\.csv/',$_GET["Items"]) >= 1 ){
        if (($handle = fopen("./data/".$_GET["Items"], "r")) !== FALSE) {
        
            $csvs = [];
            while(! feof($handle)) {
               $csvs[] = fgetcsv($handle);
            }
        
            $datas = [];
            $column_names = [];
            foreach ($csvs[0] as $single_csv) {
                $column_names[] = $single_csv;
            }
            foreach ($csvs as $key => $csv) {
                if ($key === 0) {
                    continue;
                }
                foreach ($column_names as $column_key => $column_name) {
                    $datas[$key-1][$column_name] = $csv[$column_key];
                }
            }
            $json = json_encode($datas);
            fclose($handle);
            header("Content-Type: application/json");
            print_r($json);
        }
    }
}
