<?php
// protocol-dashboard.php - generated from VIEW_BUNDLE
// Run: php -S 0.0.0.0:8082 protocol-dashboard.php

$sources = [
    "protocol" => ["uri" => "http://localhost:8080/api/v3/protocols/123", "refresh" => 1],
    "devices" => ["uri" => "http://localhost:8081/api/v3/devices", "refresh" => 5]
];

function fetchData($uri) {
    $ch = curl_init($uri);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 5);
    return json_decode(curl_exec($ch), true);
}

header("Content-Type: text/html");
?>
<!DOCTYPE html>
<html>
<head><title>Protocol Dashboard</title></head>
<body>
    <h1>Live Protocol Dashboard</h1>
    <div id="protocol"></div>
    <div id="devices"></div>
    <script>
        function updateData() {
            fetch("<?= $sources["protocol"]["uri"] ?>").then(r=>r.json()).then(d=>document.getElementById("protocol").innerHTML = "<pre>" + JSON.stringify(d, null, 2) + "</pre>");
            setTimeout(updateData, <?= $sources["protocol"]["refresh"] ?> * 1000);
        }
        updateData();
    </script>
</body>
</html>
