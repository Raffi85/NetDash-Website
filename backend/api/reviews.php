<?php
header('Content-Type: application/json');
$reviews = [
    ["name" => "Alice", "review" => "Great product!", "rating" => 5],
    ["name" => "Bob", "review" => "Helpful support team.", "rating" => 4],
    ["name" => "Charlie", "review" => "Clean interface.", "rating" => 5]
];
echo json_encode($reviews);
?>