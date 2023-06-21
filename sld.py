'''
Create Cyclomedia ready SLD from QGIS SLD
'''
from PyQt5.QtXml import (QDomDocument)  # pylint: disable=E0611

xml = '<?xml version="1.0" encoding="UTF-8"?>'
xsi_loc = "http://www.opengis.net/sld StyledLayerDescriptor.xsd"
xmlns = "http://www.opengis.net/se"
sld_url = "http://www.opengis.net/sld"
ogc = "http://www.opengis.net/ogc"
xlink = "http://www.w3.org/1999/xlink"
xsi = "http://www.w3.org/2001/XMLSchema-instance"
version = "1.1.0"


def create_sld_element(doc):
    ''' Create StyledLayerDescriptor element '''
    sld_element = doc.createElement("sld:StyledLayerDescriptor")
    attribute = doc.createAttribute("xsi:schemaLocation")
    attribute.setValue(xsi_loc)
    sld_element.setAttributeNode(attribute)
    attribute = doc.createAttribute("xmlns")
    attribute.setValue(xmlns)
    sld_element.setAttributeNode(attribute)
    attribute = doc.createAttribute("xmlns:sld")
    attribute.setValue(sld_url)
    sld_element.setAttributeNode(attribute)
    attribute = doc.createAttribute("xmlns:ogc")
    attribute.setValue(ogc)
    sld_element.setAttributeNode(attribute)
    attribute = doc.createAttribute("xmlns:xlink")
    attribute.setValue(xlink)
    sld_element.setAttributeNode(attribute)
    attribute = doc.createAttribute("xmlns:xsi")
    attribute.setValue(xsi)
    sld_element.setAttributeNode(attribute)
    attribute = doc.createAttribute("version")
    attribute.setValue(version)
    sld_element.setAttributeNode(attribute)

    return sld_element


def remove_newline(message: str) -> str:
    ''' Remove newline from a string '''
    # TODO remove whitespace should be leading and trailing, not within
    return "".join(message.splitlines()).replace("  ", "")


def create_userlayer_element(doc):
    ''' Create UserLayer document '''
    ul_element = doc.createElement("sld:UserLayer")

    return ul_element


def create_userstyle_element(doc):
    ''' Create UserStyle element '''
    us_element = doc.createElement("sld:UserStyle")

    return us_element


def node_to_string_via_domdocument(node):
    ''' Create a QDomDocument and take string from it '''
    # TODO: should work. Why not?
    doc = QDomDocument()
    doc.importNode(node, True)
    return doc.toString()


def node_to_string(node):
    ''' Create custom string from QDomNode '''
    if not node.hasChildNodes():
        if node.isText:
            return "{}".format(node.nodeValue())

        return "<{0}>{1}</{0}>".format(node.nodeName(), node.nodeValue())

    children = node.childNodes()
    children_as_text = []
    for i in range(children.length()):
        children_as_text.append(node_to_string(children.item(i)))
    children_as_text = "".join(children_as_text)
    return "<{0}>{1}</{0}>".format(node.nodeName(), children_as_text)


def find_elements_by_tag(domdocument, tag):
    ''' Find element in document '''
    return domdocument.elementsByTagName(tag)


def create_sld_description(qgis_sld_doc: QDomDocument) -> str:
    ''' Convert SLD into something Cyclomedia understands '''
    doc = QDomDocument()

    sld = create_sld_element(doc)
    doc.appendChild(sld)

    us = create_userstyle_element(doc)
    ul = create_userlayer_element(doc)
    ul.appendChild(us)
    sld.appendChild(ul)

    fs_list = find_elements_by_tag(qgis_sld_doc, "se:FeatureTypeStyle")
    if not fs_list.isEmpty():
        fs = fs_list.item(0)
        sld_node = doc.importNode(fs, True)
        us.appendChild(sld_node)
        return xml + remove_newline(doc.toString().replace("se:", ""))

    print("Error finding se:FeatureTypeStyle")
    return "error"
