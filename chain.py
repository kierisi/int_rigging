from maya import cmds
from maya import OpenMaya as om

def fkchain(parent, joints, template, color):
    joint_parent = parent

    # joints = cmds.ls(sl=True)
    # will print out the names of all joints selected in the outliner
        
    for jnt in joints:
        
        # create a control and a group for each joint and rename group and control
        grp, ctl = create_control_from_template(jnt.replace("jnt", "ctl"), joint_parent, template, color)
            
        # position the control on the joint
        #cmds.matchTransform(ctl, jnt) 
        cmds.delete(cmds.parentConstraint(jnt, grp, mo=False))
        
        joint_parent = ctl  # update value of joint_parent to 'ctl' 
            
        # drive the joint
        cmds.pointConstraint(ctl, jnt)
        cmds.orientConstraint(ctl, jnt)
        cmds.scaleConstraint(ctl, jnt)

    for side in ["lf", "rt"]:
        for phalanx in ["A", "B", "C", "D", "E"]:
            joints = []
            for i in range(4):
                jnt_name = "{0}_finger{1}0{2}_jnt".format(side, phalanx, i)
                if cmds.objExists(jnt_name):
                    joints.append(jnt_name)

def create_control_from_template(name, parent, template, color):
    # create a control and a group for each joint and rename group and control
    grp, ctl = cmds.duplicate(template, n=name.replace("ctl", "grp"), rc=True)
    # rc = rename children
    ctl = cmds.rename(ctl, name)

    # parent group under the previous control
    if parent:    # if joint_parent has a value, execute next line
        cmds.parent(grp, parent)
    
    cmds.setAttr("{0}.overrideEnabled".format(ctl), 1)
    cmds.setAttr("{0}.overrideColor".format(ctl), color)

    return grp, ctl

def place_pole_vector(polevector, jointA, jointB, jointC):
    #posA = cmds.xform("lf_arm00_jnt", q=True, t=True, ws=True)
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

def ikchain(name, side, parent, joints, iktemplate, pvtemplate, color):
    ikgrp, ikctl = create_control_from_template("{0}_{1}Ik_ctl".format(side, name), parent, iktemplate, color)
    pvgrp, pvctl = create_control_from_template("{0}_{1}Pv_ctl".format(side, name), parent, pvtemplate, color)

    cmds.delete(cmds.parentConstraint(joints[-1], ikgrp, mo=False))

    handle, effector = cmds.ikHandle(sj=joints[0], ee=joints[-1], sol="ikRPsolver")  
    cmds.parent(handle, ikctl)

    place_pole_vector(pvgrp, *joints)
    cmds.poleVectorConstraint(pvctl, handle)

    # stretch setup
    loc = cmds.spaceLocator(n="{0}_{1}Distance_LOC".format(side, name))[0]
    if parent:
        cmds.parent(loc,parent)
    
    cmds.delete(cmds.parentConstraint(joints[0], loc, mo=False))

    dbt = cmds.createNode("distanceBetween", n="{0}_{1}_DBT".format(side, name))
    cmds.connectAttr("{0}.worldMatrix[0]".format(loc), "{0}.inMatrix1".format(dbt))
    cmds.connectAttr("{0}.worldMatrix[0]".format(ikctl), "{0}.inMatrix2".format(dbt))

    stretch_factor_mdn = cmds.createNode("multiplyDivide", n="{0}_{1}StretchFactor_MDN".format(side, name))
    cmds.connectAttr("{0}.distance".format(dbt), "{0}.input1X".format(stretch_factor_mdn))
    input2x_value = cmds.getAttr("{0}.tx".format(joints[1])) + cmds.getAttr("{0}.tx".format(joints[2]))
    cmds.setAttr("{0}.input2X".format(stretch_factor_mdn), input2x_value)
    cmds.setAttr("{0}.operation".format(stretch_factor_mdn), 2)

    stretch_clamp = cmds.createNode("clamp", n="{0}_{1}StretchFactor_CLM".format(side, name))
    cmds.connectAttr("{0}.outputX".format(stretch_factor_mdn), "{0}.inputR".format(stretch_clamp))
    cmds.setAttr("{0}.minR".format(stretch_clamp), 1)
    cmds.setAttr("{0}.maxR".format(stretch_clamp), 999999)
    
    stretch_blend_colors = []
    for jnt in joints[1:]:
        jnt_stretch_mdn = cmds.createNode("multiplyDivide", n=jnt.replace("_JNT", "StretchFactor_MDN"))
        cmds.connectAttr("{0}.outputR".format(stretch_clamp), "{0}.input2X".format(jnt_stretch_mdn))
        input1x_value = cmds.getAttr("{0}.tx".format(jnt))
        cmds.setAttr("{0}.input1X".format(jnt_stretch_mdn), input1x_value)

        jnt_stretch_blc = cmds.createNode("blendColors", n=jnt.replace("_JNT", "StretchFactor_BLC"))
        cmds.setAttr("{0}.color2R".format(jnt_stretch_blc), input1x_value)
        cmds.connectAttr("{0}.outputX".format(jnt_stretch_mdn), "{0}.color1R".format(jnt_stretch_blc))

        stretch_blend_colors.append(jnt_stretch_blc)
        cmds.connectAttr("{0}.outputR".format(jnt_stretch_blc), "{0}.tx".format(jnt))
    
    # # squash setup
    # loc = cmds.spaceLocator(n="{0}_{1}Distance_LOC".format(side, name))[0]
    # if parent:
    #     cmds.parent(loc,parent)
    
    # cmds.delete(cmds.parentConstraint(joints[0], loc, mo=False))

    # dbt = cmds.createNode("distanceBetween", n="{0}_{1}_DBT".format(side, name))
    # cmds.connectAttr("{0}.worldMatrix[0]".format(loc), "{0}.inMatrix1".format(dbt))
    # cmds.connectAttr("{0}.worldMatrix[0]".format(ikctl), "{0}.inMatrix2".format(dbt))

    # stretch_factor_mdn = cmds.createNode("multiplyDivide", n="{0}_{1}StretchFactor_MDN".format(side, name))
    # cmds.connectAttr("{0}.distance".format(dbt), "{0}.input1X".format(stretch_factor_mdn))
    # input2x_value = cmds.getAttr("{0}.tx".format(joints[1])) + cmds.getAttr("{0}.tx".format(joints[2]))
    # cmds.setAttr("{0}.input2X".format(stretch_factor_mdn), input2x_value)
    # cmds.setAttr("{0}.operation".format(stretch_factor_mdn), 2)

    # stretch_clamp = cmds.createNode("clamp", n="{0}_{1}StretchFactor_CLM".format(side, name))
    # cmds.connectAttr("{0}.outputX".format(stretch_factor_mdn), "{0}.inputR".format(stretch_clamp))
    # cmds.setAttr("{0}.minR".format(stretch_clamp), 1)
    # cmds.setAttr("{0}.maxR".format(stretch_clamp), 999999)
    
    # stretch_blend_colors = []
    # for jnt in joints[1:]:
    #     jnt_stretch_mdn = cmds.createNode("multiplyDivide", n=jnt.replace("_JNT", "StretchFactorMDN"))
    #     cmds.connectAttr("{0}.outputR".format(stretch_clamp), "{0}.input2X".format(jnt_stretch_mdn))
    #     input1x_value = cmds.getAttr("{0}.tx".format(jnt))
    #     cmds.setAttr("{0}.input1X".format(jnt_stretch_mdn), input1x_value)

    #     jnt_stretch_blc = cmds.createNode("blendColors", n=jnt.replace("_JNT", "StretchFactor_BLC"))
    #     cmds.setAttr("{0}.color2R".format(jnt_stretch_blc), input1x_value)
    #     cmds.connectAttr("{0}.outputX".format(jnt_stretch_mdn), "{0}.color1R".format(jnt_stretch_blc))

    #     stretch_blend_colors.append(jnt_stretch_blc)
    #     cmds.connectAttr("{0}.outputR".format(jnt_stretch_blc), "{0}.tx".format(jnt))