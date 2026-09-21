const API_BASE = window.AGBOMI_API_BASE || '/api';
const $ = id => document.getElementById(id);
const naira = value => new Intl.NumberFormat('en-NG', { style: 'currency', currency: 'NGN' }).format(value || 0);
const getCsrf = () => document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1];

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body) headers['Content-Type'] = 'application/json';
  if (!['GET', 'HEAD'].includes(options.method || 'GET') && getCsrf()) headers['X-CSRFToken'] = getCsrf();
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers, credentials: 'include' });
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) {
    let message = data.detail || `Request failed (${response.status})`;
    if (response.status === 400 && data) {
      const errors = [];
      for (const [field, msgs] of Object.entries(data)) {
        if (Array.isArray(msgs)) errors.push(...msgs);
        else if (typeof msgs === 'string') errors.push(msgs);
      }
      if (errors.length) message = errors.join(' ');
    }
    throw Object.assign(new Error(message), { status: response.status });
  }
  return data;
}
function setMessage(text, bad = false) { const el = $('status-message') || $('auth-message') || $('review-message'); if (el) { el.textContent = text; el.style.color = bad ? '#f87171' : '#86efac'; } }
function imageUrl(value) { return !value ? 'https://via.placeholder.com/600x450?text=No+image' : value.startsWith('http') ? value : `${API_BASE}${value}`; }
function empty(container, text) { const el = document.createElement('p'); el.className = 'message'; el.textContent = text; container.replaceChildren(el); }
async function renderFooter() {
  try {
    const settings = await api('/site-settings/');
    const companyEl = $('footer-company'); if (companyEl) companyEl.textContent = settings.company_name || companyEl.textContent;
    const phoneEl = $('footer-support-phone'); if (phoneEl) phoneEl.querySelector('a').textContent = settings.support_phone ? `+${settings.support_phone.replace(/[^0-9]/g, '')}` : phoneEl.querySelector('a').textContent;
    const emailEl = $('footer-support-email'); if (emailEl) emailEl.textContent = settings.support_email || ''; if (emailEl && settings.support_email) { const a = document.createElement('a'); a.href = `mailto:${settings.support_email}`; a.textContent = settings.support_email; emailEl.replaceChildren(a); }
    const socialLinks = $('social-links'); if (!socialLinks) return;
    const urls = {
      twitter: settings.twitter_handle ? `https://x.com/${settings.twitter_handle.replace(/^@/, '')}` : null,
      facebook: settings.facebook_handle ? `https://facebook.com/${settings.facebook_handle}` : null,
      instagram: settings.instagram_handle ? `https://instagram.com/${settings.instagram_handle.replace(/^@/, '')}` : null,
      linkedin: settings.linkedin_handle ? `https://linkedin.com/in/${settings.linkedin_handle}` : null,
    };
    socialLinks.querySelectorAll('.social-link').forEach(link => {
      const platform = link.dataset.platform;
      const url = urls[platform];
      if (url) { link.href = url; link.classList.remove('hidden'); } else { link.classList.add('hidden'); }
    });
    const copyEl = $('footer-copy'); if (copyEl) copyEl.textContent = `© ${new Date().getFullYear()} ${settings.company_name || 'A M TECH SOLUTIONS'}. All rights reserved.`;
  } catch { /* footer is non-critical */ }
}
function renderStars(target, value) {
  const rating = Number(value) || 0; const rounded = Math.round(rating);
  target.replaceChildren(...Array.from({ length: 5 }, (_, index) => { const star = document.createElement('span'); star.textContent = '★'; star.className = index < rounded ? 'is-filled' : ''; return star; }));
  target.setAttribute('aria-label', rating ? `${rating.toFixed(1)} out of 5 stars` : 'No ratings yet');
}
function productCard(product, { wishlisted = false, onWishlistChange } = {}) {
  const card = document.createElement('article'); card.className = 'product-card card';
  const img = document.createElement('img'); img.src = imageUrl(product.image); img.alt = product.name;
  const body = document.createElement('div'); body.className = 'card-body';
  const title = document.createElement('h3'); title.textContent = product.name;
  const price = document.createElement('p'); price.className = 'price'; price.textContent = naira(product.current_price ?? product.sale_price ?? product.price);
  const rating = document.createElement('div'); rating.className = 'card-rating'; const stars = document.createElement('span'); stars.className = 'rating-stars'; renderStars(stars, product.rating?.average_rating); const count = document.createElement('span'); count.textContent = `(${product.rating?.total_reviews || 0})`; rating.append(stars, count);
  const actions = document.createElement('div'); actions.className = 'product-actions';
  const add = document.createElement('button'); add.type = 'button'; add.textContent = product.in_stock === false ? 'Out of stock' : 'Add to cart'; add.disabled = product.in_stock === false;
  add.onclick = async event => { event.preventDefault(); if (!await currentUser()) return requireLogin(); try { await api('/cart/items/', { method: 'POST', body: JSON.stringify({ product_id: product.id, quantity: 1 }) }); await renderHeader(); updateCartNotification(); setMessage(`${product.name} was added to your cart.`); } catch (error) { setMessage(error.message, true); } };
  const link = document.createElement('a'); link.className = 'button-link'; link.href = `product.html?slug=${encodeURIComponent(product.slug)}`; link.textContent = 'View product'; link.onclick = event => { event.preventDefault(); card.classList.add('is-clicking'); setTimeout(() => { location.href = link.href; }, 320); };
  const wishlist = document.createElement('button'); wishlist.type = 'button'; wishlist.className = 'secondary wishlist-toggle';
  const setWishlistLabel = saved => { wishlist.textContent = saved ? '♥ Saved' : '♡ Wishlist'; wishlist.setAttribute('aria-pressed', String(saved)); };
  setWishlistLabel(wishlisted);
  wishlist.onclick = async event => {
    event.preventDefault();
    if (!await currentUser()) return requireLogin();
    const saved = wishlist.getAttribute('aria-pressed') === 'true';
    try {
      await api(`/wishlist/${product.id}/`, { method: saved ? 'DELETE' : 'POST' });
      setWishlistLabel(!saved);
      setMessage(!saved ? `${product.name} was saved to your wishlist.` : `${product.name} was removed from your wishlist.`);
      if (onWishlistChange) onWishlistChange(!saved);
    } catch (error) { setMessage(error.message, true); }
  };
  actions.append(add, link, wishlist); body.append(title, price, rating, actions); card.append(img, body); return card;
}
async function currentUser() { try { return await api('/auth/me/'); } catch { return null; } }
function requireLogin() { location.href = 'auth.html'; }

function updateCartNotification() {
  const dot = document.querySelector('.cart-notification-dot');
  if (!dot) return;
  const me = $('profile-bar')?.dataset.me === 'true';
  if (!me) {
    dot.classList.remove('show');
    return;
  }
  api('/cart/').then(cart => {
    dot.classList.toggle('show', cart.items?.length > 0);
  }).catch(() => {});
}

async function renderHeader() {
  const target = $('profile-bar'); if (!target) return;
  target.classList.remove('hidden'); target.replaceChildren();
  const me = await currentUser();
  target.dataset.me = me ? 'true' : 'false';
  const cart = document.createElement('a'); cart.className = 'cart-link'; cart.href = 'cart.html'; cart.title = 'Shopping cart'; cart.setAttribute('aria-label', 'Shopping cart');
  const icon = document.createElement('span'); icon.className = 'cart-icon'; icon.setAttribute('aria-hidden', 'true'); icon.textContent = '🛒';
  const count = document.createElement('span'); count.className = 'cart-count'; count.textContent = '0'; cart.append(icon, count);
  if (me) {
    const account = document.createElement('a'); account.href = 'account.html'; account.textContent = `Hi, ${me.username}`;
    const wishlist = document.createElement('a'); wishlist.className = 'wishlist-link'; wishlist.href = 'account.html#wishlist'; wishlist.title = 'Wishlist'; wishlist.setAttribute('aria-label', 'Wishlist'); wishlist.textContent = '♡';
    const logout = document.createElement('button'); logout.className = 'secondary'; logout.textContent = 'Logout'; logout.onclick = async () => { await api('/auth/logout/', { method: 'POST' }); location.href = 'auth.html'; };
    target.append(account, wishlist, cart, logout);
    try { count.textContent = (await api('/cart/')).items.length; } catch { /* cart status is non-critical */ }
  } else { target.append(cart); }
  renderMobileNav();
  updateCartNotification();
}
function bindSearch() {
  const form = $('search-form');
  if (form) {
    form.onsubmit = event => {
      event.preventDefault();
      const term = $('search-input').value.trim();
      location.href = `index.html${term ? `?query=${encodeURIComponent(term)}` : ''}`;
    };
  }
  const mobileForm = $('mobile-search-bar')?.querySelector('form');
  if (mobileForm) {
    mobileForm.onsubmit = event => {
      event.preventDefault();
      const term = mobileForm.querySelector('input').value.trim();
      location.href = `index.html${term ? `?query=${encodeURIComponent(term)}` : ''}`;
    };
  }
}

function bindMobileMenu() {
  const toggle = $('mobile-menu-toggle');
  const nav = $('mobile-nav');
  const searchToggle = $('mobile-search-toggle');
  const searchBar = $('mobile-search-bar');
  if (toggle && nav) {
    toggle.onclick = () => nav.classList.add('open');
    nav.addEventListener('click', (e) => {
      if (e.target.classList.contains('mobile-nav-close') || e.target === nav) {
        nav.classList.remove('open');
      }
    });
  }
  if (searchToggle && searchBar) {
    searchToggle.onclick = () => searchBar.classList.toggle('open');
  }
}

function renderMobileNav() {
  const nav = $('mobile-nav');
  if (!nav) return;
  nav.replaceChildren();
  const close = document.createElement('button');
  close.className = 'mobile-nav-close';
  close.setAttribute('aria-label', 'Close menu');
  close.textContent = '✕';
  close.onclick = (e) => {
    e.stopPropagation();
    nav.classList.remove('open');
  };
  nav.appendChild(close);

  const me = $('profile-bar')?.dataset.me === 'true';
  const homeLinks = [['index.html', 'Home'], ['category.html?slug=phones', 'Phones'], ['category.html?slug=laptops', 'Laptops'], ['index.html#category-section', 'Accessories'], ['index.html#product-section', 'All Products']];
  homeLinks.forEach(([href, label]) => { const link = document.createElement('a'); link.href = href; link.textContent = label; nav.appendChild(link); });
  const phone = document.createElement('a'); phone.className = 'mobile-help'; phone.href = 'tel:+2348136239556'; phone.textContent = 'Call / WhatsApp  ·  +234 813 623 9556'; nav.appendChild(phone);
  if (me) {
    const account = document.createElement('a');
    account.href = 'account.html';
    account.textContent = 'My Account';
    const wishlist = document.createElement('a');
    wishlist.href = 'account.html#wishlist';
    wishlist.textContent = '♡ Wishlist';
    const cart = document.createElement('a');
    cart.href = 'cart.html';
    cart.textContent = '🛒 Cart';
    const logout = document.createElement('button');
    logout.className = 'secondary';
    logout.textContent = 'Logout';
    logout.onclick = async () => { await api('/auth/logout/', { method: 'POST' }); location.href = 'auth.html'; };
    nav.append(account, wishlist, cart, logout);
  } else {
    const login = document.createElement('a');
    login.href = 'auth.html';
    login.textContent = 'Login / Sign up';
    nav.appendChild(login);
  }
}

function renderBottomNav() {
  if (document.querySelector('.mobile-bottom-nav')) return;
  const nav = document.createElement('nav'); nav.className = 'mobile-bottom-nav'; nav.setAttribute('aria-label', 'Quick navigation');
  const items = [['index.html', '⌂', 'Home'], ['index.html#category-section', '▦', 'Categories'], ['cart.html', '🛒', 'Cart'], ['account.html#wishlist', '♡', 'Wishlist'], ['account.html', '◉', 'Account']];
  items.forEach(([href, icon, label]) => { const link = document.createElement('a'); link.href = href; link.innerHTML = `<span>${icon}</span><small>${label}</small>`; if (location.pathname.endsWith(href.split('#')[0])) link.classList.add('active'); nav.appendChild(link); });
  document.body.appendChild(nav);
}

async function loadHome() {
  const query = new URLSearchParams(location.search).get('query');
  const [products, categories] = await Promise.all([api(`/product_list/${query ? `?query=${encodeURIComponent(query)}` : ''}`), api('/categories/')]);
  const productGrid = $('product-grid'); productGrid.replaceChildren(...products.map(productCard)); if (!products.length) empty(productGrid, 'No products match that search.');
  const categoryGrid = $('category-grid'); categoryGrid.replaceChildren(...categories.map(category => { const card = document.createElement('a'); card.className = 'category-card card'; card.href = `category.html?slug=${encodeURIComponent(category.slug)}`; const img = document.createElement('img'); img.src = imageUrl(category.image); img.alt = ''; const title = document.createElement('span'); title.textContent = category.name; const arrow = document.createElement('span'); arrow.className = 'category-arrow'; arrow.setAttribute('aria-hidden', 'true'); arrow.textContent = '→'; card.append(img, title, arrow); return card; }));
}
async function loadCategory() {
  const slug = new URLSearchParams(location.search).get('slug'); if (!slug) throw new Error('No category was selected.');
  const category = await api(`/categories/${encodeURIComponent(slug)}/`);
  $('category-title').textContent = category.name;
  const image = document.createElement('img'); image.src = imageUrl(category.image); image.alt = category.name; $('category-image').replaceChildren(image);
  const grid = $('category-products');
  const count = $('product-count'); if (count) count.textContent = `${category.products.length} product${category.products.length === 1 ? '' : 's'}`;
  const renderProducts = products => { grid.replaceChildren(...products.map(productCard)); if (!products.length) empty(grid, 'No products are available in this category yet.'); };
  renderProducts(category.products);
  const sorter = $('category-sort'); if (sorter) sorter.onchange = () => { const products = [...category.products]; const price = item => Number(item.current_price ?? item.sale_price ?? item.price ?? 0); if (sorter.value === 'low') products.sort((a, b) => price(a) - price(b)); if (sorter.value === 'high') products.sort((a, b) => price(b) - price(a)); renderProducts(products); };
}
async function loadProduct() {
  const slug = new URLSearchParams(location.search).get('slug'); if (!slug) throw new Error('No product was selected.');
  const product = await api(`/products/${encodeURIComponent(slug)}/`);
  $('product-name').textContent = product.name; $('product-description').textContent = product.description; $('product-price').textContent = naira(product.current_price);
  const gallery = [product.image, ...(product.images || []).map(image => image.image)].filter((image, index, images) => image && images.indexOf(image) === index);
  const mainImage = $('product-image'), thumbnails = $('product-thumbnails');
  const showImage = (source, index) => { const img = document.createElement('img'); img.src = imageUrl(source); img.alt = product.name; mainImage.replaceChildren(img); mainImage.classList.remove('image-changing'); void mainImage.offsetWidth; mainImage.classList.add('image-changing'); [...thumbnails.children].forEach((button, buttonIndex) => button.classList.toggle('active', buttonIndex === index)); };
  thumbnails.replaceChildren(...gallery.map((source, index) => { const button = document.createElement('button'); button.type = 'button'; button.className = 'product-thumbnail'; button.setAttribute('aria-label', `View image ${index + 1}`); const img = document.createElement('img'); img.src = imageUrl(source); img.alt = ''; button.append(img); button.onclick = () => showImage(source, index); return button; }));
  showImage(gallery[0], 0);
  if (gallery.length > 1) { let activeImage = 0; window.setInterval(() => { activeImage = (activeImage + 1) % gallery.length; showImage(gallery[activeImage], activeImage); }, 4200); }
  const average = Number(product.rating?.average_rating) || 0; renderStars($('rating-stars'), average); $('average-rating').textContent = average.toFixed(1); $('total-reviews').textContent = product.rating?.total_reviews || 0;
  const add = $('add-cart'); add.disabled = product.stock_quantity < 1 && !product.variants.some(variant => variant.stock_quantity > 0);
  if (add.disabled) add.textContent = 'Out of stock'; else { const icon = document.createElement('span'); icon.setAttribute('aria-hidden', 'true'); icon.textContent = '🛍'; add.replaceChildren(icon, document.createTextNode(' Add to cart')); }
  const quantity = $('quantity');
  const changeQuantity = amount => { quantity.value = Math.max(1, (Number(quantity.value) || 1) + amount); };
  $('quantity-decrease').onclick = () => changeQuantity(-1); $('quantity-increase').onclick = () => changeQuantity(1);
  quantity.onchange = () => { quantity.value = Math.max(1, Number(quantity.value) || 1); };
  add.onclick = async event => { event.preventDefault(); if (!await currentUser()) return requireLogin(); try { await api('/cart/items/', { method: 'POST', body: JSON.stringify({ product_id: product.id, quantity: Number(quantity.value) || 1 }) }); updateCartNotification(); location.href = 'cart.html'; } catch (error) { setMessage(error.message, true); } };
  const wishlist = $('wishlist-button');
  const setWishlistLabel = saved => { wishlist.textContent = saved ? '♥ Saved to wishlist' : '♡ Save to wishlist'; wishlist.setAttribute('aria-pressed', String(saved)); };
  const me = await currentUser();
  let saved = false;
  if (me) { try { saved = (await api('/wishlist/')).some(item => item.product.id === product.id); } catch { /* The product remains purchasable if the wishlist cannot be loaded. */ } }
  setWishlistLabel(saved);
  wishlist.onclick = async event => {
    event.preventDefault();
    if (!await currentUser()) return requireLogin();
    const isSaved = wishlist.getAttribute('aria-pressed') === 'true';
    try { await api(`/wishlist/${product.id}/`, { method: isSaved ? 'DELETE' : 'POST' }); setWishlistLabel(!isSaved); setMessage(!isSaved ? 'Saved to your wishlist.' : 'Removed from your wishlist.'); } catch (error) { setMessage(error.message, true); }
  };
  const reviews = $('review-list'); reviews.replaceChildren(...product.reviews.map(review => { const item = document.createElement('article'); item.className = 'review-card'; const title = document.createElement('strong'); title.textContent = review.user.username; const stars = document.createElement('span'); stars.className = 'rating-stars review-stars'; renderStars(stars, review.rating); const text = document.createElement('p'); text.textContent = review.review; item.append(title, stars, text); return item; })); if (!product.reviews.length) empty(reviews, 'No reviews yet.');
  const similar = $('similar-products'); similar.replaceChildren(...product.similar_products.map(productCard)); if (!product.similar_products.length) empty(similar, 'No similar products found.');
  const reviewRating = $('review-rating'); const ratingButtons = [...$('review-star-picker').querySelectorAll('button')];
  const paintReviewStars = value => ratingButtons.forEach(button => { const selected = Number(button.dataset.rating) <= value; button.classList.toggle('is-selected', selected); button.setAttribute('aria-checked', String(Number(button.dataset.rating) === value)); });
  const saveRating = async value => {
    if (!await currentUser()) return requireLogin();
    try {
      const reviewText = $('review-text').value.trim() || `Rated ${value} out of 5 stars.`;
      const response = await api('/add_review/', { method: 'POST', body: JSON.stringify({ product_id: product.id, rating: value, review: reviewText }) });
      setMessage(response.was_created ? 'Thanks for rating this product.' : 'Your rating has been updated.');
      location.reload();
    } catch (error) { setMessage(error.message, true); }
  };
  ratingButtons.forEach(button => { const value = Number(button.dataset.rating); button.onclick = () => { reviewRating.value = value; paintReviewStars(value); saveRating(value); }; button.onmouseenter = () => paintReviewStars(value); });
  $('review-star-picker').onmouseleave = () => paintReviewStars(Number(reviewRating.value) || 0);
  $('review-form').onsubmit = event => { event.preventDefault(); if (!reviewRating.value) return setMessage('Choose a star rating above before saving your review.', true); saveRating(Number(reviewRating.value)); };
}
async function loadCart() {
  if (!await currentUser()) return requireLogin(); const cart = await api('/cart/'); const container = $('cart-items');
  container.replaceChildren(...cart.items.map(item => { const row = document.createElement('article'); row.className = 'cart-row'; const label = document.createElement('span'); label.textContent = `${item.product.name} × ${item.quantity} — ${naira(item.line_total)}`; const minus = document.createElement('button'); minus.textContent = '−'; minus.disabled = item.quantity === 1; minus.onclick = () => updateCart(item.id, item.quantity - 1); const plus = document.createElement('button'); plus.textContent = '+'; plus.onclick = () => updateCart(item.id, item.quantity + 1); const remove = document.createElement('button'); remove.className = 'secondary'; remove.textContent = 'Remove'; remove.onclick = async () => { await api(`/cart/items/${item.id}/`, { method: 'DELETE' }); loadCart(); renderHeader(); }; row.append(label, minus, plus, remove); return row; }));
  if (!cart.items.length) empty(container, 'Your cart is empty.'); $('cart-total').textContent = naira(cart.subtotal); $('checkout-link').classList.toggle('hidden', !cart.items.length);
}
async function updateCart(id, quantity) { try { await api(`/cart/items/${id}/`, { method: 'PATCH', body: JSON.stringify({ quantity }) }); await loadCart(); await renderHeader(); } catch (error) { setMessage(error.message, true); } }
async function loadCheckout() {
  if (!await currentUser()) return requireLogin();
  const addresses = await api('/addresses/');
  const select = $('shipping-address'); select.replaceChildren();
  if (!addresses.length) { $('checkout-form').classList.add('hidden'); $('address-needed').classList.remove('hidden'); return; }
  select.replaceChildren(...addresses.map(address => Object.assign(document.createElement('option'), { value: address.id, textContent: `${address.full_name}, ${address.line1}, ${address.city}, ${address.state}` })));
  const methods = await api('/payment-methods/available/'); const choices = $('payment-choices');
  const iconMap = { paystack: '▣', cash_on_delivery: '💵', bank_transfer: '🏦' };
  choices.replaceChildren(...methods.methods.map(method => { const label = document.createElement('label'); label.className = 'payment-choice'; const input = document.createElement('input'); input.type = 'radio'; input.name = 'payment-method'; input.value = method.id; input.checked = method.id === 'paystack'; const icon = document.createElement('span'); icon.className = 'method-icon'; icon.textContent = iconMap[method.id] || '▣'; icon.setAttribute('aria-hidden', 'true'); const text = document.createElement('span'); text.className = 'method-text'; const name = document.createElement('strong'); name.className = 'method-name'; name.textContent = method.name; const desc = document.createElement('small'); desc.className = 'method-desc'; desc.textContent = method.description; text.append(name, desc); if (method.id === 'paystack') { const badge = document.createElement('span'); badge.className = 'method-badge'; badge.textContent = 'Recommended'; text.append(badge); } label.append(input, icon, text); return label; }));
  const savedMethods = await api('/payment-methods/'); const savedContainer = $('saved-payment-methods');
  if (savedMethods.length) { savedContainer.classList.remove('hidden'); savedContainer.replaceChildren(...savedMethods.map(method => { const label = document.createElement('label'); label.className = 'saved-payment-choice'; const input = document.createElement('input'); input.type = 'radio'; input.name = 'payment-method'; input.value = `saved:${method.id}`; const text = document.createElement('span'); text.textContent = method.label; const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'remove-payment-method'; remove.textContent = 'Remove'; remove.onclick = async event => { event.preventDefault(); await api(`/payment-methods/${method.id}/`, { method: 'DELETE' }); loadCheckout(); }; label.append(input, text, remove); return label; })); }
  const updateQuote = async () => { try { const quote = await api('/checkout/quote/', { method: 'POST', body: JSON.stringify({ shipping_address_id: select.value, billing_address_id: select.value }) }); const summary = $('order-summary'); summary.classList.remove('hidden'); summary.textContent = `Items: ${naira(quote.subtotal)} · Delivery: ${naira(quote.shipping_fee)} · Total: ${naira(quote.total)}`; } catch (error) { setMessage(error.message, true); } };
  select.onchange = updateQuote; await updateQuote();
  const bankModal = $('bank-transfer-modal');
  const openBankModal = async () => {
    try {
      const settings = await api('/site-settings/');
      $('bank-name').textContent = settings.bank_name || '';
      $('bank-account-name').textContent = settings.bank_account_name || '';
      $('bank-account-number').textContent = settings.bank_account_number || '';
      $('bank-instructions').textContent = settings.bank_instructions || '';
      $('bank-instructions-row').classList.toggle('hidden', !settings.bank_instructions);
      bankModal.classList.remove('hidden');
    } catch (error) { setMessage(error.message, true); }
  };
  const closeBankModal = () => bankModal.classList.add('hidden');
  $('bank-modal-close').onclick = closeBankModal;
  $('bank-modal-cancel').onclick = closeBankModal;
  $('bank-modal-confirm').onclick = async () => {
    closeBankModal();
    try {
      const id = select.value;
      const order = await api('/orders/create/', { method: 'POST', body: JSON.stringify({ shipping_address_id: id, billing_address_id: id, payment_method: 'bank_transfer' }) });
      $('checkout-result').classList.remove('hidden');
      $('checkout-result').textContent = `Order ${order.number} placed successfully! Your order will be processed once payment is confirmed.`;
    } catch (error) { setMessage(error.message, true); }
  };
  bankModal.querySelector('.modal-backdrop').onclick = closeBankModal;
  $('checkout-form').onsubmit = async event => {
    event.preventDefault();
    try {
      const selectedMethod = document.querySelector('input[name="payment-method"]:checked');
      if (!selectedMethod) { setMessage('Please select a payment method.', true); return; }
      const methodValue = selectedMethod.value;
      if (methodValue === 'bank_transfer') { await openBankModal(); return; }
      const savedPaymentMethodId = methodValue.startsWith('saved:') ? Number(methodValue.slice(6)) : null;
      const paymentMethod = savedPaymentMethodId ? 'paystack' : methodValue;
      const id = select.value;
      const order = await api('/orders/create/', { method: 'POST', body: JSON.stringify({ shipping_address_id: id, billing_address_id: id, payment_method: paymentMethod }) });
      if (paymentMethod === 'cash_on_delivery') { $('checkout-result').classList.remove('hidden'); $('checkout-result').textContent = `Order ${order.number} placed successfully! You will pay when your order is delivered.`; return; }
      const payment = await api(`/orders/${order.number}/payment/initialize/`, { method: 'POST', body: JSON.stringify(savedPaymentMethodId ? { saved_payment_method_id: savedPaymentMethodId } : {}) });
      if (!payment.sandbox && payment.authorization_url) { location.assign(payment.authorization_url); return; }
      $('checkout-result').classList.remove('hidden');
      $('checkout-result').textContent = payment.payment_pending_confirmation ? `Your payment is being confirmed. This order will not be processed until Paystack confirms it.` : `Order ${order.number} is awaiting payment and will not be processed or delivered until payment succeeds. Add PAYSTACK_SECRET_KEY to enable secure card and bank payments.`;
    } catch (error) { setMessage(error.message, true); }
  };
}
async function loadAccount() {
  if (!await currentUser()) return requireLogin();
  const form = $('address-form'), panel = $('address-form-panel'), idField = $('address-id'), title = $('address-form-title');
  const closeForm = () => { form.reset(); idField.value = ''; panel.classList.add('hidden'); };
  const openForm = address => { form.reset(); idField.value = address?.id || ''; title.textContent = address ? 'Edit delivery address' : 'Add a delivery address'; if (address) ['full_name', 'phone', 'line1', 'city', 'state'].forEach(field => { form.elements[field].value = address[field] || ''; }); panel.classList.remove('hidden'); panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); };
  const redraw = async () => {
    const [addresses, orders, saved] = await Promise.all([api('/addresses/'), api('/orders/'), api('/wishlist/')]);
    const list = $('addresses'); list.replaceChildren(...addresses.map(address => { const card = document.createElement('article'); card.className = 'address-card'; const details = document.createElement('p'); details.textContent = `${address.full_name} · ${address.phone} · ${address.line1}, ${address.city}, ${address.state}`; const edit = document.createElement('button'); edit.type = 'button'; edit.textContent = 'Edit'; edit.onclick = () => openForm(address); card.append(details, edit); return card; }));
    if (!addresses.length) { empty(list, 'Add your first delivery address to make checkout faster.'); openForm(); } else closeForm();
    $('new-address-button').classList.toggle('hidden', !addresses.length);
    $('orders').replaceChildren(...orders.map(order => { const item = document.createElement('p'); const isPaid = order.payment_status === 'paid'; const isPending = order.payment_status === 'pending'; const isFailed = order.payment_status === 'failed'; let statusText = isPaid ? 'Paid' : isFailed ? 'Payment failed' : `Awaiting payment (${order.payment_method.replace('_', ' ')})`; item.textContent = `${order.number} — ${naira(order.total)} — ${statusText}${isPaid ? ` — ${order.fulfillment_status}` : ''}`; if (isFailed || (isPending && order.payment_method === 'paystack')) { const retry = document.createElement('button'); retry.type = 'button'; retry.textContent = 'Retry payment'; retry.className = 'secondary'; retry.onclick = async () => { try { await api(`/orders/${order.number}/payment/retry/`, { method: 'POST' }); setMessage('Payment retry initiated.'); redraw(); } catch (error) { setMessage(error.message, true); } }; item.append(document.createTextNode(' '), retry); } return item; }));
    const wishlist = $('wishlist'); wishlist.replaceChildren(...saved.map(item => productCard(item.product, { wishlisted: true, onWishlistChange: isSaved => { if (!isSaved) redraw(); } }))); if (!saved.length) empty(wishlist, 'Your wishlist is empty.');
  };
  $('new-address-button').onclick = () => openForm(); $('cancel-address-button').onclick = closeForm;
  await redraw(); form.onsubmit = async event => { event.preventDefault(); try { const addressId = idField.value; const endpoint = addressId ? `/addresses/${addressId}/` : '/addresses/'; await api(endpoint, { method: addressId ? 'PATCH' : 'POST', body: JSON.stringify(Object.fromEntries(new FormData(form))) }); closeForm(); await redraw(); setMessage('Address saved.'); } catch (error) { setMessage(error.message, true); } };
}
async function submitAuth(event, endpoint) {
  event.preventDefault();
  try {
    await api(endpoint, { method: 'POST', body: JSON.stringify(Object.fromEntries(new FormData(event.target))) });
    location.href = 'index.html';
  } catch (error) {
    let message = error.message;
    if (error.status === 400 && error.message.includes('already exists')) {
      message = 'An account with this username or email already exists. Try logging in instead.';
    }
    setMessage(message, true);
  }
}
function bindAuthTabs() { const login = $('login-form'), signup = $('signup-form'), loginTab = $('login-tab'), signupTab = $('signup-tab'); const show = view => { const isLogin = view === 'login'; login.classList.toggle('hidden', !isLogin); signup.classList.toggle('hidden', isLogin); loginTab.classList.toggle('active', isLogin); signupTab.classList.toggle('active', !isLogin); loginTab.setAttribute('aria-selected', String(isLogin)); signupTab.setAttribute('aria-selected', String(!isLogin)); }; loginTab.onclick = () => show('login'); signupTab.onclick = () => show('signup'); }
document.addEventListener('DOMContentLoaded', async () => { try { await api('/auth/csrf/'); bindSearch(); bindMobileMenu(); renderMobileNav(); renderBottomNav(); await renderHeader(); await renderFooter(); const page = location.pathname.split('/').pop() || 'index.html'; if (page === 'index.html') await loadHome(); else if (page === 'category.html') await loadCategory(); else if (page === 'product.html') await loadProduct(); else if (page === 'cart.html') await loadCart(); else if (page === 'checkout.html') await loadCheckout(); else if (page === 'account.html') await loadAccount(); else if (page === 'auth.html') { bindAuthTabs(); $('login-form').onsubmit = event => submitAuth(event, '/auth/login/'); $('signup-form').onsubmit = event => submitAuth(event, '/auth/register/'); } } catch (error) { setMessage(error.message, true); } });
