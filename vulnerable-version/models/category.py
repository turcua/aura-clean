"""
Aura Financial Tracker - Vulnerable Version
Category Model (WITH INTENTIONAL VULNERABILITIES)
Sprint 2: Thunder Breathing - Second Form
"""

from flask import current_app
from flask_mysqldb import MySQL
from datetime import datetime

class Category:
    """Category model with intentional security vulnerabilities"""

    def __init__(self, category_id=None, user_id=None, name=None,
                 type=None, color=None, is_default=False):
        self.id = category_id
        self.user_id = user_id
        self.name = name
        self.type = type  # 'income' or 'expense'
        self.color = color
        self.is_default = is_default
        self.created_at = None
        self.updated_at = None
    
    @staticmethod
    def create(mysql, user_id, name, type, color='#6c757d'):
        """
        VULNERABILITY: SQL Injection through string concatenation
        VULNERABILITY: XSS in name field
        VULNERABILITY: No input validation
        """
        try:
            cursor = mysql.connection.cursor()

            # VULN: SQL Injection - using string formatting
            query = f"""
                INSERT INTO categories (user_id, name, type, color)
                VALUES ({user_id}, '{name}', '{type}', '{color}')
            """
            
            cursor.execute(query)
            mysql.connection.commit()
            category_id = cursor.lastrowid
            cursor.close()
            
            return True, "Category created successfully", category_id
            
        except Exception as e:
            mysql.connection.rollback()
            # VULN: Detailed error message
            return False, f"Database error: {str(e)}", None
    
    @staticmethod
    def get_by_id(mysql, category_id):
        """
        VULNERABILITY: SQL Injection
        VULNERABILITY: No ownership verification (IDOR)
        """
        try:
            cursor = mysql.connection.cursor()
            
            # VULN: SQL Injection
            query = f"SELECT * FROM categories WHERE id = {category_id}"
            
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                category = Category(
                    category_id=result[0],
                    user_id=result[1],
                    name=result[2],
                    type=result[3],
                    color=result[4],
                    is_default=bool(result[7]) if len(result) > 7 else False
                )
                return category
            return None
            
        except Exception as e:
            return None
    
    @staticmethod
    def get_all_by_user(mysql, user_id, type=None):
        """
        Returns user's own categories plus system-wide defaults.
        VULNERABILITY: SQL Injection
        VULNERABILITY: IDOR — user_id from request, no session check
        ENH-007: includes default categories (user_id IS NULL, is_default = TRUE)
        """
        try:
            cursor = mysql.connection.cursor()

            # VULN: SQL Injection — user_id and type injected directly
            # Try full query with is_default (requires Sprint 6 schema)
            try:
                if type:
                    query = (
                        f"SELECT * FROM categories "
                        f"WHERE (user_id = {user_id} OR (is_default = TRUE AND user_id IS NULL)) "
                        f"AND type = '{type}' ORDER BY is_default ASC, name"
                    )
                else:
                    query = (
                        f"SELECT * FROM categories "
                        f"WHERE (user_id = {user_id} OR (is_default = TRUE AND user_id IS NULL)) "
                        f"ORDER BY type, is_default ASC, name"
                    )
                cursor.execute(query)
            except Exception:
                # Fallback: is_default column not yet in schema — query by user_id only
                cursor = mysql.connection.cursor()
                if type:
                    query = (
                        f"SELECT * FROM categories "
                        f"WHERE user_id = {user_id} AND type = '{type}' ORDER BY name"
                    )
                else:
                    query = (
                        f"SELECT * FROM categories "
                        f"WHERE user_id = {user_id} ORDER BY type, name"
                    )
                cursor.execute(query)

            results = cursor.fetchall()
            cursor.close()

            categories = []
            for row in results:
                category = Category(
                    category_id=row[0],
                    user_id=row[1],
                    name=row[2],
                    type=row[3],
                    color=row[4],
                    is_default=bool(row[7]) if len(row) > 7 else False
                )
                categories.append(category)

            return categories

        except Exception:
            return []
    
    @staticmethod
    def get_default_by_name(mysql, name):
        """Sprint 57 (ENH-11): scheduler-internal, mirrors secure-version's
        equivalent — looks up a shared default category by name (e.g.
        "Saving Interest") so the interest job doesn't hardcode an id.
        Not attacker-facing (never called from a route), so parameterized
        despite the rest of this file's f-string convention."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT * FROM categories WHERE user_id IS NULL AND name = %s LIMIT 1",
                (name,)
            )
            row = cursor.fetchone()
            cursor.close()
            if not row:
                return None
            return Category(
                category_id=row[0], user_id=row[1], name=row[2], type=row[3], color=row[4],
                is_default=bool(row[7]) if len(row) > 7 else False,
            )
        except Exception:
            return None

    @staticmethod
    def update(mysql, category_id, user_id, name, type, color):
        """
        VULNERABILITY: SQL Injection
        VULNERABILITY: No ownership verification
        VULNERABILITY: XSS in name
        """
        try:
            cursor = mysql.connection.cursor()

            # VULN: SQL Injection - no ownership check
            query = f"""
                UPDATE categories
                SET user_id = {user_id},
                    name = '{name}',
                    type = '{type}',
                    color = '{color}'
                WHERE id = {category_id}
            """
            
            cursor.execute(query)
            mysql.connection.commit()
            cursor.close()
            
            return True, "Category updated successfully"
            
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"
    
    @staticmethod
    def delete(mysql, category_id):
        """
        VULNERABILITY: SQL Injection
        VULNERABILITY: No ownership verification
        VULNERABILITY: No cascade check (orphaned transactions)
        """
        try:
            cursor = mysql.connection.cursor()
            
            # VULN: SQL Injection - no ownership check, no cascade handling
            query = f"DELETE FROM categories WHERE id = {category_id}"
            
            cursor.execute(query)
            mysql.connection.commit()
            cursor.close()
            
            return True, "Category deleted successfully"
            
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"
