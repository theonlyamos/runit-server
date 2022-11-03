<?php
/**
 * Description
 * @authors Amos Amissah (theonlyamos@gmail.com)
 * @date    2022-07-09 15:05:41
 * @version 1.0.0
 */

try {
    if ($argc >= 2) {
        $loader = $argv[1];
        include_once($loader);
        echo join(',', get_defined_functions()['user']);
    }
} catch (Exception $error) {
    echo $error->getMessage();
}

?>