<?php
/**
 * Plugin Name: ZICORE WooCommerce - ZNT Token Packages
 * Plugin URI: https://zicore.space
 * Description: Sells ZNT (Zitón) token packages through WooCommerce with portal discount pricing. Credits ZNT to user ZiVault accounts.
 * Version: 1.0.0
 * Author: ZiCore Systems
 * Author URI: https://zicore.space
 * License: GPL v2 or later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain: zicore-woocommerce
 * Domain Path: /languages
 * Requires at least: 5.8
 * Requires PHP: 7.4
 * WC requires at least: 6.0
 * WC tested up to: 8.5
 */

defined('ABSPATH') || exit;

define('ZICORE_WC_VERSION', '1.0.0');
define('ZICORE_WC_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('ZICORE_WC_PLUGIN_URL', plugin_dir_url(__FILE__));
define('ZICORE_API_BASE', 'https://zcs.zicore.space');

class ZICORE_WooCommerce {
    
    private static $instance = null;
    private $api_key = '';
    private $api_secret = '';
    
    public static function instance() {
        if (is_null(self::$instance)) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    private function __construct() {
        $this->api_key = get_option('zicore_wc_api_key', '');
        $this->api_secret = get_option('zicore_wc_api_secret', '');
        
        add_action('init', [$this, 'init']);
        add_action('admin_menu', [$this, 'admin_menu']);
        add_action('admin_init', [$this, 'register_settings']);
        add_action('woocommerce_product_options_general_product_data', [$this, 'add_znt_fields']);
        add_action('woocommerce_process_product_meta', [$this, 'save_znt_fields']);
        add_action('woocommerce_order_status_completed', [$this, 'on_order_complete']);
        add_action('woocommerce_order_status_processing', [$this, 'on_order_processing']);
        
        add_shortcode('zicore_znt_packages', [$this, 'znt_packages_shortcode']);
        
        register_activation_hook(__FILE__, [$this, 'activate']);
        register_deactivation_hook(__FILE__, [$this, 'deactivate']);
    }
    
    public function init() {
        if (!class_exists('WooCommerce')) {
            add_action('admin_notices', function() {
                echo '<div class="error"><p><strong>ZICORE WooCommerce</strong> requires WooCommerce to be installed and active.</p></div>';
            });
            return;
        }
        
        add_filter('woocommerce_product_data_tabs', [$this, 'add_product_tab']);
        add_action('woocommerce_product_data_panels', [$this, 'product_data_panel']);
        
        add_action('wp_ajax_zicore_znt_purchase', [$this, 'ajax_purchase']);
        add_action('wp_ajax_nopriv_zicore_znt_purchase', [$this, 'ajax_purchase']);
    }
    
    // ── ADMIN ──────────────────────────────────────────────────────────────
    
    public function admin_menu() {
        add_submenu_page(
            'woocommerce',
            'ZICORE ZNT Settings',
            'ZICORE ZNT',
            'manage_woocommerce',
            'zicore-znt',
            [$this, 'settings_page']
        );
    }
    
    public function register_settings() {
        register_setting('zicore_wc_settings', 'zicore_wc_api_key');
        register_setting('zicore_wc_settings', 'zicore_wc_api_secret');
        register_setting('zicore_wc_settings', 'zicore_wc_api_base');
        register_setting('zicore_wc_settings', 'zicore_wc_discount_percent');
        register_setting('zicore_wc_settings', 'zicore_wc_currency');
    }
    
    public function settings_page() {
        ?>
        <div class="wrap">
            <h1>ZICORE WooCommerce - ZNT Settings</h1>
            <form method="post" action="options.php">
                <?php settings_fields('zicore_wc_settings'); ?>
                <table class="form-table">
                    <tr>
                        <th scope="row">ZICORE API Base URL</th>
                        <td>
                            <input type="url" name="zicore_wc_api_base" 
                                value="<?php echo esc_attr(get_option('zicore_wc_api_base', ZICORE_API_BASE)); ?>" 
                                class="regular-text" placeholder="https://zcs.zicore.space">
                            <p class="description">Base URL of your ZICORE server (no trailing slash).</p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row">ZICORE API Key</th>
                        <td>
                            <input type="text" name="zicore_wc_api_key" 
                                value="<?php echo esc_attr($this->api_key); ?>" 
                                class="regular-text">
                            <p class="description">API key for ZICORE ZiVault authentication.</p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row">ZICORE API Secret</th>
                        <td>
                            <input type="password" name="zicore_wc_api_secret" 
                                value="<?php echo esc_attr($this->api_secret); ?>" 
                                class="regular-text">
                            <p class="description">API secret for ZICORE ZiVault authentication.</p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row">Portal Discount (%)</th>
                        <td>
                            <input type="number" name="zicore_wc_discount_percent" 
                                value="<?php echo esc_attr(get_option('zicore_wc_discount_percent', '15')); ?>" 
                                min="0" max="50" class="small-text">
                            <p class="description">Discount percentage for purchases made through the ZICORE portal.</p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row">ZNT Currency Code</th>
                        <td>
                            <input type="text" name="zicore_wc_currency" 
                                value="<?php echo esc_attr(get_option('zicore_wc_currency', 'ZNT')); ?>" 
                                class="small-text">
                            <p class="description">Currency code for ZNT token packages.</p>
                        </td>
                    </tr>
                </table>
                <?php submit_button('Save Settings'); ?>
            </form>
            
            <hr>
            <h2>Quick Stats</h2>
            <table class="widefat">
                <tr><th>Total ZNT Products</th><td><?php echo $this->count_znt_products(); ?></td></tr>
                <tr><th>Total ZNT Sold</th><td><?php echo $this->total_znt_sold(); ?> ZNT</td></tr>
                <tr><th>Revenue (MXN)</th><td>$<?php echo number_format($this->total_revenue(), 2); ?></td></tr>
            </table>
        </div>
        <?php
    }
    
    // ── PRODUCT FIELDS ─────────────────────────────────────────────────────
    
    public function add_znt_fields() {
        global $post;
        $product_type = get_post_meta($post->ID, '_product_type', true);
        
        echo '<div class="options_group">';
        woocommerce_wp_select([
            'id'          => '_znt_product_type',
            'label'       => 'ZICORE Product Type',
            'options'     => [
                ''       => 'None',
                'znt'    => 'ZNT Token Package',
                'software' => 'Software License',
                'asset'  => 'Digital Asset',
            ],
            'description' => 'Select if this is a ZICORE product type.',
        ]);
        woocommerce_wp_text_input([
            'id'          => '_znt_amount',
            'label'       => 'ZNT Amount',
            'type'        => 'number',
            'description' => 'Number of ZNT tokens included in this package.',
            'custom_attributes' => ['min' => '1'],
        ]);
        woocommerce_wp_text_input([
            'id'          => '_znt_fiat_price',
            'label'       => 'Fiat Price (MXN)',
            'type'        => 'number',
            'description' => 'Reference price in Mexican Pesos.',
            'custom_attributes' => ['step' => '0.01', 'min' => '0'],
        ]);
        echo '</div>';
    }
    
    public function save_znt_fields($post_id) {
        if (isset($_POST['_znt_product_type'])) {
            update_post_meta($post_id, '_znt_product_type', sanitize_text_field($_POST['_znt_product_type']));
        }
        if (isset($_POST['_znt_amount'])) {
            update_post_meta($post_id, '_znt_amount', absint($_POST['_znt_amount']));
        }
        if (isset($_POST['_znt_fiat_price'])) {
            update_post_meta($post_id, '_znt_fiat_price', floatval($_POST['_znt_fiat_price']));
        }
    }
    
    public function add_product_tab($tabs) {
        $tabs['zicore_znt'] = [
            'label'    => 'ZICORE ZNT',
            'target'   => 'zicore_znt_data',
            'class'    => ['show_if_znt'],
        ];
        return $tabs;
    }
    
    public function product_data_panel() {
        global $post;
        $type = get_post_meta($post->ID, '_znt_product_type', true);
        $amount = get_post_meta($post->ID, '_znt_amount', true);
        $fiat = get_post_meta($post->ID, '_znt_fiat_price', true);
        ?>
        <div id="zicore_znt_data" class="panel woocommerce_options_panel">
            <div class="options_group">
                <h3>ZNT Token Package Details</h3>
                <p><strong>Product Type:</strong> <?php echo esc_html($type ?: 'Not set'); ?></p>
                <p><strong>ZNT Amount:</strong> <?php echo esc_html($amount ?: '0'); ?> ZNT</p>
                <p><strong>Fiat Price:</strong> $<?php echo esc_html($fiat ?: '0'); ?> MXN</p>
                <p><strong>Portal Discount:</strong> <?php echo esc_html(get_option('zicore_wc_discount_percent', '15')); ?>%</p>
                <p><strong>Discounted Price:</strong> $<?php echo esc_html($fiat ? number_format($fiat * (1 - get_option('zicore_wc_discount_percent', '15') / 100), 2) : '0'); ?> MXN</p>
                <hr>
                <p class="description">
                    ZNT packages are sold through the ZICORE portal with a <?php echo esc_html(get_option('zicore_wc_discount_percent', '15')); ?>% discount.
                    Users purchase via ZICORE login and receive ZNT tokens in their ZiVault account.
                </p>
            </div>
        </div>
        <?php
    }
    
    // ── ORDER HANDLING ─────────────────────────────────────────────────────
    
    public function on_order_processing($order_id) {
        $this->process_znt_order($order_id);
    }
    
    public function on_order_complete($order_id) {
        $this->process_znt_order($order_id);
    }
    
    private function process_znt_order($order_id) {
        $order = wc_get_order($order_id);
        if (!$order) return;
        
        $already_processed = get_post_meta($order_id, '_zicore_znt_processed', true);
        if ($already_processed) return;
        
        foreach ($order->get_items() as $item) {
            $product = $item->get_product();
            if (!$product) continue;
            
            $znt_type = get_post_meta($product->get_id(), '_znt_product_type', true);
            if ($znt_type !== 'znt') continue;
            
            $znt_amount = absint(get_post_meta($product->get_id(), '_znt_amount', true));
            if ($znt_amount <= 0) continue;
            
            $billing_email = $order->get_billing_email();
            $billing_first = $order->get_billing_first_name();
            $billing_last = $order->get_billing_last_name();
            
            $this->credit_znt_to_user($billing_email, $znt_amount, $order_id);
            
            $order->add_order_note(sprintf(
                'ZICORE: Credited %d ZNT to %s via ZiVault API.',
                $znt_amount,
                $billing_email
            ));
        }
        
        update_post_meta($order_id, '_zicore_znt_processed', 'yes');
    }
    
    private function credit_znt_to_user($email, $amount, $order_id) {
        $api_base = get_option('zicore_wc_api_base', ZICORE_API_BASE);
        $api_key = get_option('zicore_wc_api_key', '');
        $api_secret = get_option('zicore_wc_api_secret', '');
        
        if (empty($api_key) || empty($api_secret)) {
            error_log('ZICORE WC: API credentials not configured. Cannot credit ZNT.');
            return false;
        }
        
        $payload = json_encode([
            'email' => $email,
            'amount' => $amount,
            'order_id' => $order_id,
            'source' => 'woocommerce',
            'description' => sprintf('ZNT purchase via WooCommerce (Order #%d)', $order_id),
        ]);
        
        $response = wp_remote_post($api_base . '/api/vault/znt/credit', [
            'timeout' => 15,
            'headers' => [
                'Content-Type' => 'application/json',
                'Authorization' => 'Bearer ' . $api_key,
                'X-API-Secret' => $api_secret,
            ],
            'body' => $payload,
        ]);
        
        if (is_wp_error($response)) {
            error_log('ZICORE WC: API error - ' . $response->get_error_message());
            return false;
        }
        
        $code = wp_remote_retrieve_response_code($response);
        $body = json_decode(wp_remote_retrieve_response_body($response), true);
        
        if ($code === 200 && isset($body['status']) && $body['status'] === 'ok') {
            error_log(sprintf('ZICORE WC: Credited %d ZNT to %s (Order #%d)', $amount, $email, $order_id));
            return true;
        } else {
            error_log(sprintf('ZICORE WC: Failed to credit ZNT to %s - %s', $email, json_encode($body)));
            return false;
        }
    }
    
    // ── SHORTCODE ──────────────────────────────────────────────────────────
    
    public function znt_packages_shortcode($atts) {
        $atts = shortcode_atts([
            'columns' => 3,
            'limit'   => -1,
        ], $atts);
        
        $products = wc_get_products([
            'limit'    => $atts['limit'],
            'status'   => 'publish',
            'meta_key' => '_znt_product_type',
            'meta_value' => 'znt',
            'orderby'  => 'meta_value_num',
            'order'    => 'ASC',
            'meta_query' => [
                ['key' => '_znt_amount', 'compare' => 'EXISTS'],
            ],
        ]);
        
        if (empty($products)) {
            return '<p>No ZNT token packages available at this time.</p>';
        }
        
        ob_start();
        echo '<div class="zicore-znt-grid" style="display:grid;grid-template-columns:repeat(' . intval($atts['columns']) . ',1fr);gap:20px;margin:20px 0;">';
        
        foreach ($products as $product) {
            $amount = get_post_meta($product->get_id(), '_znt_amount', true);
            $fiat = get_post_meta($product->get_id(), '_znt_fiat_price', true);
            $discount = get_option('zicore_wc_discount_percent', '15');
            $discounted = $fiat ? $fiat * (1 - $discount / 100) : $product->get_price();
            $image = wp_get_attachment_image_src($product->get_image_id(), 'woocommerce_thumbnail');
            $permalink = $product->get_permalink();
            
            ?>
            <div class="zicore-znt-card" style="background:#0d1117;border:1px solid #1e2a3a;border-radius:12px;overflow:hidden;text-align:center;padding:24px;">
                <?php if ($image): ?>
                    <img src="<?php echo esc_url($image[0]); ?>" alt="<?php echo esc_attr($product->get_name()); ?>" style="width:100%;height:160px;object-fit:cover;border-radius:8px;margin-bottom:16px;">
                <?php endif; ?>
                
                <h3 style="color:#e0e6f0;font-size:16px;margin:0 0 8px;"><?php echo esc_html($product->get_name()); ?></h3>
                
                <div style="color:#00e5ff;font-size:28px;font-weight:700;margin:12px 0;">
                    <?php echo esc_html($amount); ?> <span style="font-size:14px;color:#6b7280;">ZNT</span>
                </div>
                
                <div style="margin:12px 0;">
                    <span style="text-decoration:line-through;color:#6b7280;font-size:14px;">$<?php echo esc_html(number_format($fiat, 2)); ?> MXN</span>
                    <span style="color:#00ff88;font-size:20px;font-weight:600;margin-left:8px;">$<?php echo esc_html(number_format($discounted, 2)); ?> MXN</span>
                    <span style="background:#ff4444;color:white;font-size:10px;padding:2px 6px;border-radius:4px;margin-left:4px;">-<?php echo esc_html($discount); ?>%</span>
                </div>
                
                <p style="color:#9ca3af;font-size:12px;margin:8px 0 16px;">
                    Discounted price for ZICORE portal purchases
                </p>
                
                <a href="<?php echo esc_url($permalink); ?>" 
                   style="display:inline-block;background:#00e5ff;color:#0d1117;padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:600;font-size:13px;">
                    View Package
                </a>
            </div>
            <?php
        }
        
        echo '</div>';
        return ob_get_clean();
    }
    
    // ── HELPERS ────────────────────────────────────────────────────────────
    
    private function count_znt_products() {
        return wc_get_products([
            'limit' => -1,
            'status' => 'publish',
            'meta_key' => '_znt_product_type',
            'meta_value' => 'znt',
            'return' => 'ids',
        ]) ? count(wc_get_products([
            'limit' => -1,
            'status' => 'publish',
            'meta_key' => '_znt_product_type',
            'meta_value' => 'znt',
            'return' => 'ids',
        ])) : 0;
    }
    
    private function total_znt_sold() {
        global $wpdb;
        $total = 0;
        $orders = wc_get_orders(['status' => ['completed', 'processing'], 'limit' => -1]);
        foreach ($orders as $order) {
            foreach ($order->get_items() as $item) {
                $product = $item->get_product();
                if (!$product) continue;
                $znt_type = get_post_meta($product->get_id(), '_znt_product_type', true);
                if ($znt_type === 'znt') {
                    $amount = absint(get_post_meta($product->get_id(), '_znt_amount', true));
                    $total += $amount * $item->get_quantity();
                }
            }
        }
        return $total;
    }
    
    private function total_revenue() {
        $total = 0;
        $orders = wc_get_orders(['status' => ['completed', 'processing'], 'limit' => -1]);
        foreach ($orders as $order) {
            foreach ($order->get_items() as $item) {
                $product = $item->get_product();
                if (!$product) continue;
                $znt_type = get_post_meta($product->get_id(), '_znt_product_type', true);
                if ($znt_type === 'znt') {
                    $total += $order->get_total() * ($item->get_quantity() / $order->get_item_count());
                }
            }
        }
        return $total;
    }
    
    public function activate() {
        add_option('zicore_wc_api_base', ZICORE_API_BASE);
        add_option('zicore_wc_discount_percent', '15');
        add_option('zicore_wc_currency', 'ZNT');
    }
    
    public function deactivate() {
        delete_option('zicore_wc_api_key');
        delete_option('zicore_wc_api_secret');
    }
}

ZICORE_WooCommerce::instance();
