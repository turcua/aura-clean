"""
Aura Financial Tracker - Secure Version
Category Model
Sprint 11: Core Financial Tracking

Security properties (contrast with vulnerable-version/models/category.py):
- All queries parameterized (%s placeholders) — no string interpolation
- Ownership enforced in the SQL WHERE clause itself (id = %s AND user_id = %s),
  not just checked separately in the route — a global default (user_id IS NULL)
  can never match a real user_id, so defaults are structurally uneditable/undeletable
- No mass assignment — user_id is never accepted as a parameter to update()
"""


class Category:
    """Category model with secure query construction and ownership enforcement."""

    def __init__(self, category_id=None, user_id=None, name=None,
                 type=None, color=None, is_default=False):
        self.id = category_id
        self.user_id = user_id
        self.name = name
        self.type = type
        self.color = color
        self.is_default = is_default
        self.created_at = None
        self.updated_at = None

    @staticmethod
    def create(mysql, user_id, name, type, color='#6c757d'):
        """Create a category owned by user_id. Returns (success, message, category_id)."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO categories (user_id, name, type, color) VALUES (%s, %s, %s, %s)",
                (user_id, name, type, color)
            )
            mysql.connection.commit()
            category_id = cursor.lastrowid
            cursor.close()
            return True, "Category created successfully", category_id
        except Exception as e:
            mysql.connection.rollback()
            if 'uq_user_name_type' in str(e) or 'Duplicate entry' in str(e):
                return False, "You already have a category with that name and type", None
            return False, "Could not create category", None

    @staticmethod
    def get_by_id(mysql, category_id, user_id):
        """
        Fetch a category by ID, scoped to categories this user can see
        (their own, or a system-wide default). Returns None if not found or not visible.
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, name, type, color, is_default FROM categories "
                "WHERE id = %s AND (user_id = %s OR (is_default = TRUE AND user_id IS NULL))",
                (category_id, user_id)
            )
            row = cursor.fetchone()
            cursor.close()
            return Category._from_row(row) if row else None
        except Exception:
            return None

    @staticmethod
    def get_all_by_user(mysql, user_id, type=None):
        """Returns the user's own categories plus system-wide defaults."""
        try:
            cursor = mysql.connection.cursor()
            if type:
                cursor.execute(
                    "SELECT id, user_id, name, type, color, is_default FROM categories "
                    "WHERE (user_id = %s OR (is_default = TRUE AND user_id IS NULL)) AND type = %s "
                    "ORDER BY is_default ASC, name",
                    (user_id, type)
                )
            else:
                cursor.execute(
                    "SELECT id, user_id, name, type, color, is_default FROM categories "
                    "WHERE (user_id = %s OR (is_default = TRUE AND user_id IS NULL)) "
                    "ORDER BY type, is_default ASC, name",
                    (user_id,)
                )
            rows = cursor.fetchall()
            cursor.close()
            return [Category._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def update(mysql, category_id, user_id, name, type, color):
        """
        Update a category — scoped to `id = %s AND user_id = %s` so a user can
        only ever affect their own categories. Rows against a default (user_id
        IS NULL) never match a real user_id, so defaults cannot be edited this way.
        Returns (success, message).
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE categories SET name = %s, type = %s, color = %s "
                "WHERE id = %s AND user_id = %s",
                (name, type, color, category_id, user_id)
            )
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Category not found or you don't have permission to edit it"
            return True, "Category updated successfully"
        except Exception as e:
            mysql.connection.rollback()
            if 'uq_user_name_type' in str(e) or 'Duplicate entry' in str(e):
                return False, "You already have a category with that name and type"
            return False, "Could not update category"

    @staticmethod
    def delete(mysql, category_id, user_id):
        """
        Delete a category — scoped to `id = %s AND user_id = %s`. Transactions
        referencing it are set to NULL (uncategorized) by the FK ON DELETE SET NULL,
        never orphaned. Returns (success, message).
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "DELETE FROM categories WHERE id = %s AND user_id = %s",
                (category_id, user_id)
            )
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Category not found or you don't have permission to delete it"
            return True, "Category deleted successfully"
        except Exception:
            mysql.connection.rollback()
            return False, "Could not delete category"

    @staticmethod
    def get_default_by_name(mysql, name):
        """Sprint 57 (ENH-11): scheduler-internal — looks up a shared
        default category by name (e.g. "Saving Interest"), so the interest
        job doesn't hardcode a category id that could differ across
        environments. Returns None if no such default category exists
        (the job falls back to an uncategorized transaction rather than
        failing outright — see run_interest_job())."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, name, type, color, is_default FROM categories "
                "WHERE user_id IS NULL AND name = %s LIMIT 1",
                (name,)
            )
            row = cursor.fetchone()
            cursor.close()
            return Category._from_row(row) if row else None
        except Exception:
            return None

    @staticmethod
    def get_all_defaults(mysql):
        """Sprint 57 (ENH-02): admin panel — every shared default category
        (user_id IS NULL), which get_all_by_user() already includes
        alongside a user's own but with no way to tell them apart or
        manage them directly. This is the admin-only counterpart: no
        user_id scoping at all, by design, since these rows apply to
        every user in the app."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, name, type, color, is_default FROM categories "
                "WHERE user_id IS NULL ORDER BY type, name"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [Category._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def create_default(mysql, name, type, color='#6c757d'):
        """Sprint 57 (ENH-02): admin panel — create a new shared default
        category (user_id NULL, is_default TRUE), visible to every user
        immediately via get_all_by_user()'s existing OR (is_default = TRUE
        AND user_id IS NULL) clause. Returns (success, message, category_id)."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO categories (user_id, name, type, color, is_default) VALUES (NULL, %s, %s, %s, TRUE)",
                (name, type, color)
            )
            mysql.connection.commit()
            category_id = cursor.lastrowid
            cursor.close()
            return True, "Default category created successfully", category_id
        except Exception as e:
            mysql.connection.rollback()
            if 'uq_user_name_type' in str(e) or 'Duplicate entry' in str(e):
                return False, "A default category with that name and type already exists", None
            return False, "Could not create default category", None

    @staticmethod
    def update_default(mysql, category_id, name, type, color):
        """Sprint 57 (ENH-02): admin panel — update a shared default
        category. Scoped to `id = %s AND user_id IS NULL`, the mirror
        image of update()'s `user_id = %s` scoping — this is the one path
        in the app that CAN affect a default, precisely because it's
        gated behind api_admin_required, not because the ownership check
        was loosened. Returns (success, message)."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE categories SET name = %s, type = %s, color = %s "
                "WHERE id = %s AND user_id IS NULL",
                (name, type, color, category_id)
            )
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Default category not found"
            return True, "Default category updated successfully"
        except Exception as e:
            mysql.connection.rollback()
            if 'uq_user_name_type' in str(e) or 'Duplicate entry' in str(e):
                return False, "A default category with that name and type already exists"
            return False, "Could not update default category"

    @staticmethod
    def delete_default(mysql, category_id):
        """Sprint 57 (ENH-02): admin panel — delete a shared default
        category. Scoped to `id = %s AND user_id IS NULL`, same reasoning
        as update_default(). Every transaction across every user that used
        this category gets set to NULL (uncategorized) by the existing FK
        ON DELETE SET NULL — non-destructive to transaction data itself,
        but affects every user who had it, not just one; the route calling
        this is responsible for warning about that scope before it's ever
        reached. Returns (success, message)."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("DELETE FROM categories WHERE id = %s AND user_id IS NULL", (category_id,))
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Default category not found"
            return True, "Default category deleted successfully"
        except Exception:
            mysql.connection.rollback()
            return False, "Could not delete default category"

    @staticmethod
    def _from_row(row):
        return Category(
            category_id=row[0],
            user_id=row[1],
            name=row[2],
            type=row[3],
            color=row[4],
            is_default=bool(row[5]),
        )
