from PySide2 import QtGui, QtWidgets, QtCore
import stateutils
# Steps

redshiftMappings = {
    "mapConnections" :{
        "basecolor" : {
            "input" : "base_color",
            "output" : "outColor"
        },
        "emitcolor" : {
            "input" : "emission_color",
            "output" : "outColor"
        },
        "rough" : {
            "input" : "refl_roughness",
            "output" : "outColor"
        },
        "baseNormal" : {
            "input" : "bump_input",
            "output" : "out"
        },
        "metallic" : {
            "input" : "metalness",
            "output" : "outColor"
        }
    }
}

class RSConverted(QtWidgets.QWidget):
    def __init__(self):
        super(RSConverted, self).__init__()
        self.init_ui()

    def init_ui(self):
        #self.setMinimumSize(750, 500)
        self.sizePolicy().setVerticalPolicy(QtWidgets.QSizePolicy.Minimum)
        self.sizePolicy().setHorizontalPolicy(QtWidgets.QSizePolicy.Minimum)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Labs Preferences")

        #Layout
        self.main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.main_layout)
        self.setAcceptDrops(True)

        self.mat_layout = QtWidgets.QHBoxLayout()

        self.mat_lbl = QtWidgets.QLabel("Material Network:")
        self.mat_layout.addWidget(self.mat_lbl)
        self.mat_layout.addSpacing(50)

        #QLine Edit
        self.mat_net = utilityQLineEdit()
        self.mat_net.textChanged.connect(self.update_text_call)
        self.mat_net.setFixedWidth(200)
        self.mat_layout.addWidget(self.mat_net)

        #Display List of Items
        # self.list_wdgt = QtWidgets.QScrollArea()
        # self.list_wdgt.setFixedHeight(100)
        # #

        self.list_layout = QtWidgets.QVBoxLayout()
        self.list_wdgt = QtWidgets.QListWidget()
        self.list_layout.addWidget(self.list_wdgt)
        self.list_wdgt.setFixedHeight(150)


        #Button layout
        self.button_layout = QtWidgets.QHBoxLayout()
        self.bottom_btn_layout = QtWidgets.QHBoxLayout()
        self.convert_btn = QtWidgets.QPushButton("Convert")
        self.update_btn = QtWidgets.QPushButton("Update Materials")
        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        self.remove_btn = QtWidgets.QPushButton("Remove")

        self.convert_btn.clicked.connect(self.connect_call)
        self.remove_btn.clicked.connect(self.remove_call)
        self.refresh_btn.clicked.connect(self.refresh_call)
        self.update_btn.clicked.connect(self.update_call)

        self.bottom_btn_layout.addWidget(self.convert_btn)
        self.bottom_btn_layout.addWidget(self.update_btn)

        self.button_layout.addWidget(self.refresh_btn)
        self.button_layout.setSpacing(25)
        self.button_layout.addWidget(self.remove_btn)

        self.main_layout.addLayout(self.mat_layout)
        self.main_layout.setSpacing(25)
        self.main_layout.addLayout(self.list_layout)
        self.main_layout.setSpacing(25)
        self.main_layout.addLayout(self.button_layout)
        self.main_layout.addWidget(lineSep())
        self.main_layout.addLayout(self.bottom_btn_layout)

        #Update QLineEdit
        start_selected = self.check_selected()
        if(start_selected):
            self.populate_list(hou.selectedNodes()[0])

        #Size our UI.
        self.setMaximumSize(self.baseSize()) #Base size after init the UI.

    def check_selected(self):
        if(len(hou.selectedNodes()) == 1):
            if(hou.selectedNodes()[0].type().name() == "matnet"):
                self.mat_net.setText(hou.selectedNodes()[0].path())
                self.adjust_line_size()
                return True
        else:
            return False

    def populate_list(self, node):
        if(len(node.children()) > 0):
            self.list_wdgt.clear()
            for child in node.children():
                self.list_wdgt.addItem(child.name())

    def connect_call(self):
        if(self.list_wdgt.count() > 0):
            for i in range(self.list_wdgt.count()):
                item_text = self.list_wdgt.item(i).text()
                ref_node = hou.node(self.mat_net.text() + "/" + item_text)
                if(ref_node):
                    self.texture_convert(ref_node)

    def update_call(self):
        if(len(hou.selectedNodes()) == 1):
            container = hou.selectedNodes()[0].parent()
            if(container):
                update_mat = container.createNode("material", "Update_Material")
                if(update_mat):
                    selec = hou.selectedNodes()[0]
                    orig_pos = selec.position()
                    update_mat.setPosition(hou.Vector2(orig_pos[0], orig_pos[1]-2))
                    update_mat.setInput(0, selec)

                    multi_parm = update_mat.parm('num_materials')
                    print(multi_parm)

                    shop_mat_path = selec.geometry().findPrimAttrib("shop_materialpath")
                    if(shop_mat_path):
                        multi_parm.removeMultiParmInstance(0)
                        for i,val in enumerate(shop_mat_path.strings()):
                            group_string = "@shop_materialpath=" + val
                            multi_parm.insertMultiParmInstance(i)
                            update_mat.parm('group'+ str(i+1)).set(group_string)
                            
                            search_term = val.split("/")[-1]
                            search_area = hou.node(self.mat_net.text())
                            if(search_area):
                                rs_mat = search_area.glob("*" + search_term + "*")
                                if(len(rs_mat) > 0):
                                    for node in rs_mat:
                                        if node.type().name() == "redshift_vopnet":
                                            update_mat.parm('shop_materialpath' + str(i+1)).set(node.path())
                            else:
                                hou.ui.displayMessage("Please have a valid material network to search.")
        else:
            hou.ui.displayMessage("Select a single SOP node.")

    def texture_convert(self, node):
        for child in node.children():
            if(child.type().name() == "principledshader::2.0"):
                normal_path = self.gather_normal(child)
                tex_nodes = self.gather_textures(child)

                self.create_rs_tex(node.name(), tex_nodes, normal_path)

    def create_rs_tex(self, name, textures, normal):
        rs_prex = "rs_"
        context = hou.node(self.mat_net.text())
        if(context):
            rs_node = context.createNode("redshift_vopnet", rs_prex + name)
            rs_node.moveToGoodPosition()
            if(rs_node):
                for i, tex in enumerate(textures[0]):
                    standard_mat = rs_node.node("StandardMaterial1")
                    file_name = textures[1][i]
                    tex_sampler = rs_node.createNode("redshift::TextureSampler", file_name)
                    if(tex_sampler):
                        tex_sampler.moveToGoodPosition()
                        tex_sampler.parm("tex0").set(tex)
                        if file_name in redshiftMappings["mapConnections"].keys():
                            tex_params = redshiftMappings["mapConnections"][file_name]
                            
                            if file_name == "baseNormal":
                                normalNode = rs_node.createNode("redshift::BumpMap")
                                normalNode.parm("inputType").set("1")
                                normalNode.setNamedInput("input", tex_sampler, "outColor")
                                normalNode.moveToGoodPosition()
                                standard_mat.setNamedInput(tex_params["input"], normalNode, tex_params["output"])
                            else:
                                standard_mat.setNamedInput(tex_params["input"], tex_sampler, tex_params["output"])


    def gather_textures(self, node):
        parms = node.globParms("*useTexture*", search_label=True)
        tex_parms = []
        tex_names = []
        for parm in parms:
            if(parm.eval() == 1):
                tex_path = parm.path().split("useTexture")[0] + "texture"
                tex_parm = node.parm(tex_path)
                if(tex_parm):
                    tex_parms.append(tex_parm.evalAsString())
                    tex_names.append(parm.name().split("useTexture")[0][:-1])
        return [tex_parms, tex_names]
    
    def gather_normal(self, node):
        parms = node.globParms("*baseBumpAndNormal_enable*", search_label=True)
        if(parms[0].eval() == 1):
            tex_node = node.parm(parms[0].path().replace("baseBumpAndNormal_enable", "baseNormal_texture"))
            tex_path = tex_node.evalAsString()
            return tex_path

    def refresh_call(self):
        if(self.mat_net.text() != ""):
            refresh_node = hou.node(self.mat_net.text())
            self.populate_list(refresh_node)

    def remove_call(self):
        listItems = self.list_wdgt.selectedItems()
        for item in listItems:
            self.list_wdgt.takeItem(self.list_wdgt.row(item))

    def update_text_call(self, new_text):
        new_node = hou.node(new_text)
        if(new_node):
            self.populate_list(new_node)

    #Drop functionality for elsewhere on the UI.
    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        mime_data = event.mimeData()
        data = mime_data.data(hou.qt.mimeType.nodePath)
        if(data):
            node_path = str(data).split("\\t")
            if(len(node_path)>1):
                hou.ui.displayMessage("Please only drag one node.")
            else:
                mat_node = node_path[0]
                if(mat_node[0] == 'b'):
                    mat_node = mat_node[1:]
                mat_node = mat_node.strip("'")
                #Create Node Object from given string
                new_node = hou.node(mat_node)
                if(new_node.type().name() == "matnet"):
                    #Set the info here.
                    self.mat_net.clear()
                    self.mat_net.setText(new_node.path())

                    #Make sure we resize to be big enough.
                    self.adjust_line_size()

                    self.populate_list(new_node)
                else:
                    hou.ui.displayMessage("Please provide a matnet.")

    def adjust_line_size(self):
        default_font = self.mat_net.font() #Returns QFont object.
        mat_net_text = self.mat_net.displayText() #Returns a QString object.

        mat_net_font_metrics = QtGui.QFontMetrics(default_font)
        new_width = mat_net_font_metrics.horizontalAdvance(mat_net_text) + 25

        if (new_width > self.mat_net.width()):
            self.mat_net.setFixedWidth(new_width)

class lineSep(QtWidgets.QFrame):
    def __init__(self):
        super(lineSep, self).__init__()
        self.setFrameShape(QtWidgets.QFrame.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)

#Subclass the QLineEdit to implement checking, runs a separate Widget drop event, compared to dropping on the rest of the UI.
class utilityQLineEdit(QtWidgets.QLineEdit):
    def __init__(self, parent = None):
        super().__init__(parent)

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        mime_data = event.mimeData()
        data = mime_data.data(hou.qt.mimeType.nodePath)
        if(data):
            node_path = str(data).split("\\t")
            if(len(node_path)>1):
                hou.ui.displayMessage("Please only drag one node.")
            else:
                mat_node = node_path[0]
                if(mat_node[0] == 'b'):
                    mat_node = mat_node[1:]
                mat_node = mat_node.strip("'")
                #Create Node Object from given string
                new_node = hou.node(mat_node)
                if(new_node.type().name() == "matnet"):
                    #Set the info here.
                    self.clear()
                    self.setText(new_node.path())

                    #Make sure we resize to be big enough.
                    default_font = self.font() #Returns QFont object.
                    mat_net_text = self.displayText() #Returns a QString object.

                    mat_net_font_metrics = QtGui.QFontMetrics(default_font)
                    new_width = mat_net_font_metrics.horizontalAdvance(mat_net_text) + 25

                    if (new_width > self.width()):
                        self.setFixedWidth(new_width)
                else:
                    hou.ui.displayMessage("Please provide a matnet.")

window = RSConverted()
window.show()