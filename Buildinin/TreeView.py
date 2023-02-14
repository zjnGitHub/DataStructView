import time

import PySide6
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtGui import QCursor, QBrush, QColor, QPen
from PySide6.QtCore import Qt, QPointF, QTimeLine, QTime, QCoreApplication, QEventLoop, QPoint, Property, \
    QPropertyAnimation
from PySide6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsItemAnimation

from DataStructView.Buildinin.TreeItem import TreeNode, TreeLine


class TreeView(QGraphicsView):
    def __init__(self, parent=None):
        super(TreeView, self).__init__(parent)

        # 初始化
        self.mouse = Qt.MouseButton.NoButton  # 记录鼠标事件
        self._enlarge = 0  # 放大的次数
        self._shrink = 0  # 缩小的次数
        self.last_pos = QtCore.QPointF()  # 作用 -> 记录鼠标位置，移动view
        self.select_node = None

        # 设置Setting
        if not self.isInteractive(): print("MyGraphicsView: 没有开启场景交互功能")  # 判断有没有进行场景交互
        self.setScene(QGraphicsScene(self.x(), self.y(), self.width(), self.height(), self))  # 内置一个场景
        self.viewport().setProperty("cursor", QCursor(Qt.CrossCursor))  # 设置光标为十字型  ( + )

        self.default_node = TreeNode()
        self.scene().addItem(self.default_node)
        self.default_node.setPos(0, -300)
        self.default_node.curScene = self.scene()

        self.y_spacing = self.default_node.boundingRect().center().y() + 50  # y间距
        self.x_spacing = self.default_node.boundingRect().center().x()  # x间距
        self.ratio = 2  # 间距比例(数值越大)

    # 鼠标点击事件
    def mousePressEvent(self, event: PySide6.QtGui.QMouseEvent) -> None:
        """
        左键：
            1. 第一次点击该节点
            2. 第二次点击该节点
        中键：
            1. 保存点击的位置用于移动视图
        右键：
            1. 右键被选中的节点 -> 删除
        详细内容：
        在用户左键点击一个节点时则选中该节点，若他再次点击该节点或者点击空白位置则取消选择
        用户选中一个节点后对该节点右键则会删除该节点，然后该节点下的所有节点都将被删除
        用户中键将记录点击的位置，长按可以移动视图
        """
        self.mouse = event.button()
        item = self.itemAt(event.pos())
        if event.button() == Qt.MiddleButton:
            self.last_pos = self.mapToScene(event.pos())
            return
        elif event.button() == Qt.MouseButton.LeftButton:
            if type(item) == TreeNode and item != self.select_node:
                if self.select_node: self.select_node.setBrush(QBrush(QColor(58, 143, 192)))
                self.select_node = item
                self.select_node.setBrush(QBrush(Qt.red))
            elif type(item) == TreeNode and item == self.select_node:
                ...
        elif event.button() == Qt.MouseButton.RightButton:
            if item == self.select_node:
                ...

    # 鼠标双击事件
    def mouseDoubleClickEvent(self, event: PySide6.QtGui.QMouseEvent) -> None:
        item = self.itemAt(event.pos())
        # 点击节点
        if item and type(item) == TreeNode:
            # 创建左孩子
            if event.button() == Qt.MouseButton.LeftButton:
                if item.left is None:
                    self.createNode(item, 'l')
                # print("双击左键")
            # 创建右孩子
            elif event.button() == Qt.MouseButton.RightButton:
                if item.right is None:
                    self.createNode(item, 'r')
                # print("双击右键")

    # 鼠标点击后长按移动事件
    def mouseMoveEvent(self, event: PySide6.QtGui.QMouseEvent) -> None:
        if self.mouse == Qt.MiddleButton:
            dp = self.mapToScene(event.pos()) - self.last_pos
            sRect = self.sceneRect()
            self.setSceneRect(sRect.x() - dp.x(), sRect.y() - dp.y(), sRect.width(), sRect.height())
            self.last_pos = self.mapToScene(event.pos())
            return
        QGraphicsView.mouseMoveEvent(self, event)

    # 滚轮
    def wheelEvent(self, event) -> None:
        # 等比例缩放
        wheelValue = event.angleDelta().y()
        ratio = wheelValue / 1200 + 1  # ratio -> 1.1 or 0.9
        if ratio > 1:  # 放大次数6
            if self._enlarge < 6:
                self._enlarge += 1
                self._shrink -= 1
                self.scale(ratio, ratio)
        else:  # 缩小次数10
            if self._shrink < 10:
                self._shrink += 1
                self._enlarge -= 1
                self.scale(ratio, ratio)

    # 鼠标释放事件
    def mouseReleaseEvent(self, event: PySide6.QtGui.QMouseEvent) -> None:
        self.mouse = Qt.MouseButton.NoButton

    def createNode(self, node: TreeNode, directions: str):
        # 当前节点为最后一层，要重新绘制所有节点的位置
        if node.cur_layer == node.max_layer and node != self.default_node:
            self.redraw()
        if directions != 'l' and directions != 'r':
            print("TreeView: createNode的directions传进了一个非'l'和'r'的directions")
            return
        new_node = self.get_newNode(node, directions)  # 新节点
        self.scene().addItem(new_node)
        new_node.setPos(self.calculated_pos(new_node, directions))
        # 线连接
        line = TreeLine(node, new_node)
        self.scene().addItem(line)
        line.curScene = self.scene()
        if directions == 'l':
            node.l_line = line
        else:
            node.r_line = line
        new_node.p_line = line

    def redraw(self):
        """
        这个方法主要时防止二叉树节点的增多带来的交叉，只有在最后一层节点增加时才调用该方法
        """
        root = self.default_node
        q = []
        if root.left: q.append((root.left, 'l'))
        if root.right: q.append((root.right, 'r'))

        while q:
            temp = []
            for node, directions in q:
                node.max_layer += 1
                node.setPos(self.calculated_pos(node, directions))
                self.change_node_line(node)
                if node.left:
                    temp.append((node.left, 'l'))
                if node.right:
                    temp.append((node.right, 'r'))
            q = temp

    # 创建一个新的节点并将数据处理好
    def get_newNode(self, node: TreeNode, directions: str) -> TreeNode:
        new_node = TreeNode()
        self.scene().addItem(new_node)
        new_node.parent = node
        new_node.curScene = self.scene()
        if directions == 'l':
            node.left = new_node
        else:
            node.right = new_node

        new_node.cur_layer = node.cur_layer + 1
        new_node.max_layer = max(new_node.cur_layer, node.max_layer)  # 当前层数与父节点取最大
        return new_node

    # 计算节点的坐标
    def calculated_pos(self, node: TreeNode, directions: str) -> QPointF:
        # 计算间隔比例
        space_between = pow(self.ratio, node.max_layer - (node.cur_layer - 1)) - 2
        # x坐标 = 父节点x坐标 +/- (间距比例 * x间隔) +/- 节点的半径
        # y坐标 = 父节点的y坐标 +/- 固定的行距
        r = node.boundingRect().center().x()
        x_parent = node.parent.pos().x()
        y_parent = node.parent.pos().y()
        x = x_parent - (space_between * self.x_spacing) - r if directions == 'l' else x_parent + (
                space_between * self.x_spacing) + r
        y = y_parent + self.y_spacing
        pos = QPointF(x, y)
        return pos

    # 改变节点线条
    def change_node_line(self, node: TreeNode):
        if node.parent:
            node.p_line.change()
        if node.left:
            node.l_line.change()
        if node.right:
            node.r_line.change()

    def button_to_preorder(self):
        self.traversal_color('start')
        self.preorder_traversal(self.select_node)  # 启动前序遍历
        self.traversal_color('end')

    def button_to_inorder(self):
        self.traversal_color('start')
        self.inorder_traversal(self.select_node)  # 启动中序遍历
        self.traversal_color('end')

    def button_to_postorder(self):
        self.traversal_color('start')
        self.postorder_traversal(self.select_node)  # 启动后序遍历
        self.traversal_color('end')

    # 前序遍历
    def preorder_traversal(self, node: TreeNode) -> None:
        if node is None: return
        if node.p_line:
            node.p_line.traversal()
        node.traversal_animation()
        if node.left:
            self.preorder_traversal(node.left)
        if node.right:
            self.preorder_traversal(node.right)

    def inorder_traversal(self, node: TreeNode):
        ...

    def postorder_traversal(self, node: TreeNode):
        ...

    def traversal_color(self, color_set: str):
        """
        color_set: 可以输入 'start' 和 'end' 两种参数

        start: 将节点及边颜色改为绿色以达到效果
        end: 将节点及边颜色还原
        """
        if color_set != 'start' and color_set != 'end':
            print("Error: color_set参数传入错误，请在 'start' 和 'end' 中选一个")
        root = self.default_node
        node_color = QBrush(QColor(0, 255, 0)) if color_set == 'start' else QBrush(QColor(58, 143, 192))
        line_color = QColor(0, 255, 0) if color_set == 'start' else Qt.black
        root.setBrush(node_color)
        q = []
        if root.left: q.append((root.left, 'l'))
        if root.right: q.append((root.right, 'r'))
        while q:
            temp = []
            for node, direction in q:
                node.setBrush(node_color)
                node.p_line.setPen(QPen(line_color))
                if node.left:
                    temp.append((node.left, 'l'))
                    node.l_line.setPen(QPen(line_color))
                if node.right:
                    temp.append((node.right, 'r'))
                    node.r_line.setPen(QPen(line_color))
            q = temp
