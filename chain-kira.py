from maya import cmds
from maya import OpenMaya as om

def fkchain(parent, joints, template, color, settings_shape):
    controls =[]
    joint_parent = parent

    for jnt in joints:
        grp, ctrl = create_control_from_template(jnt.replace("JNT", "CTRL"), joint_parent, template, color, settings_shape)
       
        cmds.delete(cmds.parentConstraint(jnt, grp, mo=False))
       
        joint_parent = ctrl
        controls.append(ctrl)
       
        cmds.pointConstraint(ctrl, jnt)
        cmds.orientConstraint(ctrl, jnt)
        cmds.scaleConstraint(ctrl, jnt)

    return controls
      
def create_control_from_template(name, parent, template, color, settings_node):
    grp, ctrl = cmds.duplicate(template, n=name.replace("CTRL", "GRP"), rc=True)
    ctrl = cmds.rename(ctrl, name)

    if parent:
        cmds.parent(grp, parent)

    if settings_node:
        cmds.parent(settings_node, ctrl, s=True, r=True, add=True)

    cmds.setAttr("{0}.overrideEnabled".format(ctrl), 1)
    cmds.setAttr("{0}.overrideColor".format(ctrl), color)

    return grp, ctrl

def place_pole_vector(polevector, jointA, jointB, jointC):
    OA = om.MVector(*cmds.xform(jointA, q=True, t=True, ws=True))
    OB = om.MVector(*cmds.xform(jointB, q=True, t=True, ws=True))
    OC = om.MVector(*cmds.xform(jointC, q=True, t=True, ws=True))

    AC = OC - OA
    AB = OB - OA
    BC = OC - OB

    multiplier = (AC*AB)/(AC*AC)
    projection = AC * multiplier + OA
    direction = (OB - projection).normal()

    length = AB.length() + BC.length()
    pv_pos = OB + direction*length

    cmds.xform(polevector, t=[pv_pos.x, pv_pos.y, pv_pos.z], ws=True)


def ikchain(name, side, parent, joints, iktemplate, pvtemplate, color, settings_node=None):
    ikgrp, ikctrl = create_control_from_template("{0}_{1}Ik_CTRL".format(side, name), parent, iktemplate, color, settings_node)
    pvgrp, pvctrl = create_control_from_template("{0}_{1}Pv_CTRL".format(side, name), parent, pvtemplate, color, settings_node)

    cmds.delete(cmds.parentConstraint(joints[-1], ikgrp, mo=False))

    handle, effector = cmds.ikHandle(sj=joints[0], ee=joints[-1], sol= "ikRPsolver")
    cmds.parent(handle, ikctrl)

    place_pole_vector(pvgrp, *joints)
    cmds.poleVectorConstraint(pvctrl, handle)

    if settings_node:
        cmds.addAttr(settings_node, at="double", ln="autoStretch", min=0, max=1, dv=0, k=True)
        cmds.addAttr(settings_node, at="double", ln="autoSquash", min=0, max=1, dv=0, k=True)
        cmds.addAttr(settings_node, at="double", ln="upperLength", dv=1, k=True)
        cmds.addAttr(settings_node, at="double", ln="lowerLength", dv=1, k=True)
        cmds.addAttr(settings_node, at="double", ln="pinToPv", min=0, max=1, dv=0, k=True)

    #stretch setup
    loc = cmds.spaceLocator(n ="{0}_{1}Distance_LOC".format(side, name))[0]
    if parent:
        cmds.parent(loc, parent)

    cmds.delete(cmds.parentConstraint(joints[0], loc, mo=False))
    
    dbt = cmds.createNode("distanceBetween", n="{0}_{1}_DBT".format(side, name))
    cmds.connectAttr("{0}.worldMatrix[0]".format(loc), "{0}.inMatrix1".format(dbt))
    cmds.connectAttr("{0}.worldMatrix[0]".format(ikctrl), "{0}.inMatrix2".format(dbt))

    stretch_factor_mdn = cmds.createNode("multiplyDivide", n="{0}_{1}stretch_factor_MDN".format(side, name))
    cmds.connectAttr("{0}.distance".format(dbt), "{0}.input1X".format(stretch_factor_mdn))
    input2x_value = cmds.getAttr("{0}.tx".format(joints[1]))+  cmds.getAttr("{0}.tx".format(joints[2]))
    cmds.setAttr("{0}.input2X".format(stretch_factor_mdn), input2x_value)
    cmds.setAttr("{0}.operation".format(stretch_factor_mdn), 2)

    stretch_clamp = cmds.createNode("clamp", n="{0}_{1}StretchFactor_CLM".format(side, name))
    cmds.connectAttr("{0}.outputX".format(stretch_factor_mdn), "{0}.inputR".format(stretch_clamp))
    cmds.setAttr("{0}.minR".format(stretch_clamp), 1)
    cmds.setAttr("{0}.maxR".format(stretch_clamp), 999999)

    stretch_blend_colors = []
    for jnt in joints[1:]:
        jnt_stretch_mdn = cmds.createNode("multiplyDivide", n=jnt.replace("_JNT", "stretchFactor_MDN"))#was stretch_factor
        cmds.connectAttr("{0}.outputR".format(stretch_clamp), "{0}.input2X".format(jnt_stretch_mdn))
        input1x_value = cmds.getAttr("{0}.tx".format(jnt))
        cmds.setAttr("{0}.input1X".format(jnt_stretch_mdn), input1x_value)

        jnt_stretch_blc = cmds.createNode("blendColors", n=jnt.replace("_JNT", "StretchFactor_BLC"))
        cmds.setAttr("{0}.color2R".format(jnt_stretch_blc), input1x_value)
        cmds.connectAttr("{0}.outputX".format(jnt_stretch_mdn), "{0}.color1R".format(jnt_stretch_blc))
        cmds.connectAttr("{0}.autoStretch".format(settings_node), "{0}.blender".format(jnt_stretch_blc))

        stretch_blend_colors.append(jnt_stretch_blc)

    #squash setup
    squash_factor_mdn = cmds.createNode("multiplyDivide", n="{0}_{1}squashFactor_MDN".format(side, name))
    cmds.connectAttr("{0}.distance".format(dbt), "{0}.input2X".format(squash_factor_mdn))
    input2x_value = cmds.getAttr("{0}.tx".format(joints[1]))+  cmds.getAttr("{0}.tx".format(joints[2]))
    cmds.setAttr("{0}.input1X".format(squash_factor_mdn), input2x_value)
    cmds.setAttr("{0}.operation".format(squash_factor_mdn), 2)

    squash_clamp = cmds.createNode("clamp", n="{0}_{1}SquashFactor_CLM".format(side, name))
    cmds.connectAttr("{0}.outputX".format(squash_factor_mdn), "{0}.inputR".format(squash_clamp))
    cmds.setAttr("{0}.minR".format(squash_clamp), 0)
    cmds.setAttr("{0}.maxR".format(squash_clamp), 1)

    for jnt in joints[:-1]:
        jnt_squash_blc = cmds.createNode("blendColors", n=jnt.replace("_JNT", "squash_factor_BLC"))
        cmds.setAttr("{0}.color2R".format(jnt_squash_blc), 1)
        cmds.connectAttr("{0}.outputR".format(squash_clamp), "{0}.color1R".format(jnt_squash_blc))
        cmds.connectAttr("{0}.autoSquash".format(settings_node), "{0}.blender".format(jnt_squash_blc))

        
        cmds.connectAttr("{0}.outputR".format(jnt_squash_blc), "{0}.sy".format(jnt))
        cmds.connectAttr("{0}.outputR".format(jnt_squash_blc), "{0}.sz".format(jnt))

    #Upper Arm Length
    upper_arm_mdn = cmds.createNode("multiplyDivide", n="{0}_{1}UpperLength_MDN".format(side, name))
    cmds.connectAttr("{0}.outputR".format(stretch_blend_colors[0]), "{0}.input1X".format(upper_arm_mdn))
    cmds.connectAttr("{0}.upperLength".format(settings_node), "{0}.input2X".format(upper_arm_mdn))

    
    #Lower Arm Length
    lower_arm_mdn = cmds.createNode("multiplyDivide", n="{0}_{1}LowerLength_MDN".format(side, name))
    cmds.connectAttr("{0}.outputR".format(stretch_blend_colors[1]), "{0}.input1X".format(lower_arm_mdn))
    cmds.connectAttr("{0}.lowerLength".format(settings_node), "{0}.input2X".format(lower_arm_mdn))
    
    #pin to pv
    upper_pv_dbt = cmds.createNode("distanceBetween", n="{0}_{1}UpperPinPV_DBT".format(side, name))
    cmds.connectAttr("{0}.worldMatrix[0]".format(loc), "{0}.inMatrix1".format(upper_pv_dbt))
    cmds.connectAttr("{0}.worldMatrix[0]".format(pvctrl), "{0}.inMatrix2".format(upper_pv_dbt))

    jnt1_pinpv_blc = cmds.createNode("blendColors", n="{0}_{1}UpperPinPV_BLC".format(side, name))
    cmds.connectAttr("{0}.outputX".format(upper_arm_mdn), "{0}.color2R".format(jnt1_pinpv_blc))
    cmds.connectAttr("{0}.distance".format(upper_pv_dbt), "{0}.color1R".format(jnt1_pinpv_blc))
    cmds.connectAttr("{0}.pinToPv".format(settings_node), "{0}.blender".format(jnt1_pinpv_blc))
    cmds.connectAttr("{0}.outputR".format(jnt1_pinpv_blc), "{0}.tx".format(joints[1]))


    lower_pv_dbt = cmds.createNode("distanceBetween", n="{0}_{1}LowerPinPV_DBT".format(side, name))
    cmds.connectAttr("{0}.worldMatrix[0]".format(ikctrl), "{0}.inMatrix1".format(lower_pv_dbt))
    cmds.connectAttr("{0}.worldMatrix[0]".format(pvctrl), "{0}.inMatrix2".format(lower_pv_dbt))

    jnt2_pinpv_blc = cmds.createNode("blendColors", n="{0}_{1}LowerPinPV_BLC".format(side, name))
    cmds.connectAttr("{0}.outputX".format(lower_arm_mdn), "{0}.color2R".format(jnt2_pinpv_blc))
    cmds.connectAttr("{0}.distance".format(lower_pv_dbt), "{0}.color1R".format(jnt2_pinpv_blc))
    cmds.connectAttr("{0}pinToPv".format(settings_node), "{0}.blender".format(jnt2_pinpv_blc))
    cmds.connectAttr("{0}.outputR".format(jnt2_pinpv_blc), "{0}.tx".format(joints[2]))

    return ikctrl, pvctrl


def ikfkchain(name, side, parent, joints, fktemplate, iktemplate, pvtemplate, fkcolor, ikcolor):
    rig_group = cmds.createNode("transform", n="{0}_{1}_GRP".format(side, name))
    if parent:
        cmds.parent(rig_group, parent)

    #settings shape
    settings_loc = cmds.spaceLocator(n="{0}_{1}Settings_LOC".format(side, name))
    cmds.parent(settings_loc, rig_group)
    settings_shape = cmds.listRelatives(settings_loc, c=True, s=True)[0]
    cmds.addAttr(settings_shape, at="double", ln="ik", min=0, max=1, dv=0, k=True)

    #duplicate chains
    ik_drivers_grp = cmds.createNode("transform", n="{0}_{1}IkRig_GRP".format(side, name))
    cmds.parent(ik_drivers_grp, rig_group)

    fk_joints = duplicate_chain(joints, rig_group, "_JNT", "Fk_JNT")
    ik_driver_joints = duplicate_chain(joints, ik_drivers_grp, "_JNT", "IkDriver_JNT")
    ik_joints = duplicate_chain(joints, rig_group, "_JNT", "ik_JNT")
    blend_joints = duplicate_chain(joints, rig_group, "_JNT", "Blend_JNT")

    #connect blend chains
    for fkjnt, ikjnt, bjnt in zip(fk_joints, ik_joints, blend_joints):
        for transformation in ["translate", "rotate", "scale"]:
            blc = cmds.createNode("blendColors", n=bjnt.replace("_JNT", "{0}_JNT".format(transformation.capitalize())))
            cmds.connectAttr("{0}.{1}".format(ikjnt, transformation), "{0}.color1".format(blc))
            cmds.connectAttr("{0}.{1}".format(fkjnt, transformation), "{0}.color2".format(blc))
            cmds.connectAttr("{0}.ik".format(settings_shape), "{0}.blender".format(blc))
            cmds.connectAttr("{0}.output".format(blc), "{0}.{1}".format(bjnt, transformation))

    for ikdjnt, ikjnt in zip(ik_driver_joints, ik_joints):
        cmds.pointConstraint(ikdjnt, ikjnt)
        cmds.orientConstraint(ikdjnt, ikjnt)
        cmds.scaleConstraint(ikdjnt, ikjnt)

    for bjnt, jnt in zip(blend_joints, joints):
        cmds.pointConstraint(bjnt, jnt)
        cmds.orientConstraint(bjnt, jnt)
        cmds.connectAttr("{0}.scale".format(bjnt), "{0}.scale".format(jnt))

    fkcontrols = fkchain(rig_group, fk_joints, fktemplate, fkcolor, settings_shape)
    ikctrl, pvctrl = ikchain(name, side, rig_group, ik_driver_joints, iktemplate, pvtemplate, ikcolor, settings_shape)

    #controls visibility
    rvr = cmds.createNode("reverse", n="{0}_{1}FkIk_RVR".format(side, name))
    cmds.connectAttr("{0}.ik".format(settings_shape), "{0}.inputX".format(rvr))

    for ctrl in [ikctrl, pvctrl1]:
        grp = cmds.listRelatives(ctrl, p=True)[0]
        cmds.connectAttr("{0}.ik".format(settings_shape), "{0}.v".format(grp))

    grp = cmds.listRelatives(fkcontrols[0], p=True)[0]
    cmds.connectAttr("{0}.outputX".format(rvr), "{0}.v".format(grp))

def duplicate_chain(joints, parent, replace_what, replace_with):
    new_joints = []
    new_joints_parent = parent

    for jnt in joints:
        new_jnt = cmds.duplicate(jnt, n=jnt.replace(replace_what, replace_with), po=True)[0]

        if new_joints_parent:
            cmds.parent(new_jnt, new_joints_parent)

        new_joints_parent = new_jnt
        new_joints.append(new_jnt)

    return new_joints