<?php
header('Content-Type: application/json');
$plans = [
    ["name" => "Basic", "price" => "$0", "features" => ["1 user", "Basic analytics"]],
    ["name" => "Pro", "price" => "$9.99", "features" => ["5 users", "Advanced analytics", "Priority support"]],
    ["name" => "Enterprise", "price" => "$49.99", "features" => ["Unlimited users", "Full analytics suite", "Dedicated support"]],
];
echo json_encode($plans);
?>