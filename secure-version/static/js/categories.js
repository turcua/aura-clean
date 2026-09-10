/**
 * Aura Financial Tracker - Secure Version
 * Categories page controller
 * Sprint 11 (bugfix): moved out of an inline <script> block.
 *
 * The page's CSP is `script-src 'self' https://cdn.jsdelivr.net` — no
 * 'unsafe-inline'. An inline <script> block, and inline onclick="..."
 * attributes on dynamically-created HTML, are both blocked by that policy
 * with no visible error in some browser/console configurations. This file
 * is loaded as an external <script src>, which the CSP already permits, and
 * every interactive element below is wired with addEventListener rather
 * than an onclick attribute — no inline script anywhere.
 */

document.addEventListener('DOMContentLoaded', function() {
    loadCategories('expense');
    loadCategories('income');
    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById('saveCategoryBtn').addEventListener('click', saveCategory);
    document.getElementById('updateCategoryBtn').addEventListener('click', updateCategory);

    document.getElementById('add_category_color').addEventListener('input', function() {
        document.getElementById('add_color_preview').style.backgroundColor = this.value;
    });
    document.getElementById('edit_category_color').addEventListener('input', function() {
        document.getElementById('edit_color_preview').style.backgroundColor = this.value;
    });
}

function loadCategories(type) {
    const containerId = type === 'expense' ? 'expenseCategoriesList' : 'incomeCategoriesList';
    const container = document.getElementById(containerId);

    fetch(`/api/categories/list?type=${type}`)
        .then(response => response.json())
        .then(data => {
            container.innerHTML = '';
            if (!data.success) {
                container.appendChild(textNode(`Error loading categories: ${data.message}`, 'col-12 text-center', 'var(--dn)'));
                return;
            }
            if (data.categories.length === 0) {
                container.appendChild(textNode(`No ${type} categories yet. Click "Add Category" to create one!`, 'col-12 text-center py-5', 'var(--th)'));
                return;
            }
            data.categories.forEach(category => {
                container.appendChild(createCategoryCard(category));
            });
        })
        .catch(error => {
            container.innerHTML = '';
            container.appendChild(textNode(`Error: ${error.message}`, 'col-12 text-center', 'var(--dn)'));
        });
}

function textNode(text, className, color) {
    const div = document.createElement('div');
    div.className = className;
    if (color) div.style.color = color;
    const p = document.createElement('p');
    p.className = 'mb-0';
    p.textContent = text;
    div.appendChild(p);
    return div;
}

function createCategoryCard(category) {
    const col = document.createElement('div');
    col.className = 'glass-card';
    col.style.padding = '18px';

    const header = document.createElement('div');
    header.style.cssText = 'display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;';

    const left = document.createElement('div');
    left.style.cssText = 'display:flex;align-items:center;gap:8px;';

    const dot = document.createElement('span');
    dot.className = 'colour-dot';
    dot.style.background = category.color;

    const nameSpan = document.createElement('span');
    nameSpan.style.cssText = 'font-weight:600;font-size:0.875rem;';
    nameSpan.textContent = category.name;

    left.appendChild(dot);
    left.appendChild(nameSpan);

    const badge = document.createElement('span');
    badge.className = category.type === 'income' ? 'glass-badge badge-income' : 'glass-badge badge-expense';
    badge.textContent = category.type;

    header.appendChild(left);
    header.appendChild(badge);
    col.appendChild(header);

    if (category.is_default) {
        const wrap = document.createElement('div');
        wrap.className = 'text-center mt-3';
        const defBadge = document.createElement('span');
        defBadge.className = 'glass-badge';
        defBadge.textContent = 'System Default';
        wrap.appendChild(defBadge);
        col.appendChild(wrap);
    } else {
        const actions = document.createElement('div');
        actions.className = 'd-flex gap-2 mt-3';

        const editBtn = document.createElement('button');
        editBtn.type = 'button';
        editBtn.className = 'btn btn-sm btn-secondary flex-fill';
        editBtn.textContent = 'Edit';
        editBtn.addEventListener('click', () => openEditModal(category.id));

        const delBtn = document.createElement('button');
        delBtn.type = 'button';
        delBtn.className = 'btn btn-sm btn-secondary flex-fill';
        delBtn.textContent = 'Delete';
        delBtn.addEventListener('click', () => deleteCategory(category.id, category.name));

        actions.appendChild(editBtn);
        actions.appendChild(delBtn);
        col.appendChild(actions);
    }

    return col;
}

function saveCategory() {
    const form = document.getElementById('addCategoryForm');
    const formData = new FormData(form);
    const data = {
        name: formData.get('name'),
        type: formData.get('type'),
        color: formData.get('color'),
    };

    const saveBtn = document.getElementById('saveCategoryBtn');
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';

    fetch('/api/categories/create', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            Swal.fire({icon:'success', title:'Category Created!', text:data.message, timer:2000, showConfirmButton:false});
            bootstrap.Modal.getInstance(document.getElementById('addCategoryModal')).hide();
            form.reset();
            document.getElementById('add_category_color').value = '#3d7bff';
            document.getElementById('add_color_preview').style.backgroundColor = '#3d7bff';
            loadCategories(formData.get('type'));
        } else {
            Swal.fire({icon:'error', title:'Error!', text:data.message});
        }
    })
    .catch(error => {
        Swal.fire({icon:'error', title:'Error!', text:'Failed to save category: ' + error.message});
    })
    .finally(() => {
        saveBtn.disabled = false;
        saveBtn.textContent = 'Save Category';
    });
}

function openEditModal(categoryId) {
    fetch(`/api/categories/${categoryId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const category = data.category;
                document.getElementById('edit_category_id').value = category.id;
                document.getElementById('edit_category_name').value = category.name;
                document.getElementById('edit_category_color').value = category.color;
                document.getElementById('edit_color_preview').style.backgroundColor = category.color;
                if (category.type === 'income') {
                    document.getElementById('edit_type_income').checked = true;
                } else {
                    document.getElementById('edit_type_expense').checked = true;
                }
                new bootstrap.Modal(document.getElementById('editCategoryModal')).show();
            } else {
                Swal.fire({icon:'error', title:'Error!', text:'Failed to load category: ' + data.message});
            }
        })
        .catch(error => {
            Swal.fire({icon:'error', title:'Error!', text:'Failed to fetch category: ' + error.message});
        });
}

function updateCategory() {
    const form = document.getElementById('editCategoryForm');
    const formData = new FormData(form);
    const categoryId = formData.get('category_id');
    const data = {
        name: formData.get('name'),
        type: formData.get('type'),
        color: formData.get('color'),
    };

    const updateBtn = document.getElementById('updateCategoryBtn');
    updateBtn.disabled = true;
    updateBtn.textContent = 'Updating...';

    fetch(`/api/categories/${categoryId}/update`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            Swal.fire({icon:'success', title:'Category Updated!', text:data.message, timer:2000, showConfirmButton:false});
            bootstrap.Modal.getInstance(document.getElementById('editCategoryModal')).hide();
            loadCategories(formData.get('type'));
        } else {
            Swal.fire({icon:'error', title:'Error!', text:data.message});
        }
    })
    .catch(error => {
        Swal.fire({icon:'error', title:'Error!', text:'Failed to update category: ' + error.message});
    })
    .finally(() => {
        updateBtn.disabled = false;
        updateBtn.textContent = 'Update Category';
    });
}

function deleteCategory(categoryId, categoryName) {
    Swal.fire({
        title: 'Delete Category?',
        text: `Are you sure you want to delete "${categoryName}"? This action cannot be undone!`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc3545',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Yes, delete it!',
        cancelButtonText: 'Cancel'
    }).then((result) => {
        if (result.isConfirmed) {
            Swal.fire({title:'Deleting...', allowOutsideClick:false, didOpen:()=>Swal.showLoading()});
            fetch(`/api/categories/${categoryId}/delete`, {method:'POST'})
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        Swal.fire({icon:'success', title:'Deleted!', text:data.message, timer:2000, showConfirmButton:false});
                        loadCategories('expense');
                        loadCategories('income');
                    } else {
                        Swal.fire({icon:'error', title:'Error!', text:data.message});
                    }
                })
                .catch(error => {
                    Swal.fire({icon:'error', title:'Error!', text:'Failed to delete category: ' + error.message});
                });
        }
    });
}
