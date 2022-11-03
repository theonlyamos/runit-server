<?php
    $ch = curl_init();
    $url = 'http://localhost:9000/get_app_requests/';
    $header = ['Accept' => 'application/json'];

    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    
    $result = curl_exec($ch);
    curl_close($ch);

    $args = json_decode($result, true);
    $_GET = $args['GET'];
    $_POST = $args['POST'];

