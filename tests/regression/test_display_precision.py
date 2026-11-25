import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from nasdaq_research.presentation.main_window import display_text
from PySide6.QtCore import Qt, QSortFilterProxyModel
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QApplication

class DisplayTests(unittest.TestCase):
    def test_display(self):
        self.assertEqual(display_text(1, 6.590000153), '6.59')
        self.assertEqual(display_text(2, 10.2006711), '10.20')
        self.assertEqual(display_text(3, 5), '5')
        self.assertEqual(display_text(4, .1895340355), '0.189534')
        self.assertEqual(display_text(5, .06700570321), '0.067006')
        self.assertEqual(display_text(6, 6), '6')
        self.assertEqual(display_text(7, 63.91137187), '63.91')
        self.assertEqual(display_text(8, 1.37808), '1.38')
        self.assertEqual(display_text(9, 950000), '950,000.00')
        self.assertEqual(display_text(4, None), 'N/A')
        self.assertEqual(display_text(4, float('nan')), 'N/A')
        self.assertEqual(display_text(4, 0), '0.000000')
        self.assertNotEqual(float(display_text(4, 0.00000001)), 0)
    def test_numeric_sort(self):
        app = QApplication.instance() or QApplication([])
        model = QStandardItemModel()
        for value in (10.004, 2.0, 10.001):
            item = QStandardItem(display_text(2, value))
            item.setData(value, Qt.ItemDataRole.UserRole)
            model.appendRow(item)
        proxy = QSortFilterProxyModel()
        proxy.setSourceModel(model)
        proxy.setSortRole(Qt.ItemDataRole.UserRole)
        proxy.sort(0, Qt.SortOrder.AscendingOrder)
        self.assertEqual([proxy.index(i,0).data(Qt.ItemDataRole.UserRole) for i in range(3)], [2.0, 10.001, 10.004])
if __name__ == '__main__': unittest.main()
