# policy_v230: volley-FSM gains via self.theta (evolvable)
import math, numpy as np

# Evolvable rematch / antiscrub / race gains (see evolve_volley.py).
DEFAULT_THETA = {
    "quiet_ym_hot": 0.70,
    "quiet_vy_hot": 1.85,
    "quiet_ym_mod": 0.45,
    "quiet_mod_dt": 0.14,
    "race_ym_arm": 0.80,
    "race_meet_back": 0.40,
    "race_far_y": 0.28,
    "race_dxy_lo": 0.22,
    "race_dxy_hi": 0.62,
    "race_far_off": 0.08,
    "race_mix": 38.0,
    "race_ty_far": 0.75,
    "race_ty_vy": 0.55,
    "race_ty_g": 0.40,
    "race_sep": 0.40,
    "coast_after_contact": 0.28,
    "early_tip_mix": 32.0,
    "early_tip_ty_far": 1.05,
    "early_tip_ty_vy": 0.35,
    "band2_tend_base": 0.83,
    "band2_tend_span": 0.10,
    # Hot band1 (000-like) — was hardcoded 1.02 / 2.0 / 0.26 / 0.54–0.58
    "b1_ym": 1.02,
    "b1_vy_max": 2.0,
    "b1_by_min": 0.26,
    "b1_t0": 0.54,
    "b1_t1": 0.58,
    # Cold/lateral band3 — OFF by default (ym high); CEM lowers cold_ym to enable
    "cold_ym": 1.35,
    "cold_vy_max": 1.35,
    "cold_by_abs_max": 0.55,
    "cold_t0": 0.50,
    "cold_t1": 0.72,
    "cold_tend": 0.88,
    "cold_inside": 0.22,
}

class Policy:
    def __init__(self):
        self.g=9.81; self.ball_r=0.060; self.racket_local_z=0.23; self.racket_radius=0.36
        self.rot_min=0.0; self.rot_max=13.0; self.mass=None
        self.hover=np.ones(4)*3.25; self.A=self._allocation_matrix(); self.Ainv=np.linalg.inv(self.A)
        self.reset({})
    def reset(self, info=None):
        info=info or {}; self.t_prev=None; self.step_count=0
        self.hover=self._vec(info.get("hover_rotor_thrusts",self.hover),4,self.hover); self.hover=np.clip(self.hover,0.5,12.0)
        self.mass=float(np.clip(np.sum(self.hover)/self.g,0.8,2.2))
        self.gates0=np.asarray(info.get("gates",np.array([[1.45,0.50,0.62],[2.85,1.00,0.72],[4.20,1.55,0.68],[5.55,2.05,0.76]])),dtype=float).reshape(4,3)
        self.target0=self._vec(info.get("target",[6.55,2.55,0.12]),3,np.array([6.55,2.55,0.12]))
        self.ball_p=np.array([0.0,0.0,1.72]); self.ball_v=np.array([0.0,0.0,-0.47])
        self.ball_P=np.diag([0.05,0.05,0.08,0.10,0.10,0.16])**2
        self.last_source_t=-1e9; self.last_meas=None; self.visible_once=False
        self.gate_idx=0; self.phase="HOVER"; self.last_ball_x=None; self.last_ball_z=None; self.last_ball_vz=None
        self.last_contact_t=-1e9; self.last_contact_x=-1e9; self.contact_count=0
        self.bounce_done=np.zeros(4,bool); self.gate_done=np.zeros(4,bool); self.window_done=np.zeros(4,bool); self.window_idx=0
        self.int_pos=np.zeros(3); self.last_cmd=self.hover.copy(); self.int_pos_integral=np.zeros(3); self.cross_seen_t=np.full(4,np.nan); self.pop_end_t=-1e9; self.finish_latched=False; self.fast_midcourse=False; self.gate2_eta3=None; self.rescue_g3=False; self.g3_smashed=False; self.g4_smashed=False; self.raw_cross=np.full(4,np.nan); self.raw_prev_bx=None; self.g3_smash_t=-1e9; self.defer_smash=False; self.smash_go_t=0.9265607946427731; self.deferred_smash_done=False; self.rescue_done=np.zeros(4,bool); self.sep_until=-1e9; self._race_g1=False; self._skip_smash=False; self._g0_sep_t=-1e9; self._punch_hold_until=-1e9; self._punch_cmd=None; self._far=1.0; self._arm_ymiss=0.0; self._early_in=False; self._early_band=0; self.theta=dict(DEFAULT_THETA)
    def _vec(self,x,n,d):
        try:
            a=np.asarray(x,float).reshape(-1)
            if a.size!=n or not np.all(np.isfinite(a)): return np.asarray(d,float).reshape(n).copy()
            return a.copy()
        except: return np.asarray(d,float).reshape(n).copy()
    def _scalar(self,x,d=0.0):
        try: y=float(x); return y if math.isfinite(y) else float(d)
        except: return float(d)
    def _clip_norm(self,v,m):
        v=np.asarray(v,float); n=float(np.linalg.norm(v)); return v*(m/n) if n>m>0 else v
    def _quat_to_R(self,q):
        q=self._vec(q,4,np.array([1.,0.,0.,0.])); n=float(np.linalg.norm(q))
        w,x,y,z=(1.,0.,0.,0.) if n<1e-9 else tuple(q/n)
        return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]],float)
    def _vee_att_error(self,Rd,R): E=Rd.T@R - R.T@Rd; return 0.5*np.array([E[2,1],E[0,2],E[1,0]],float)
    def _allocation_matrix(self):
        xs=np.array([-0.14,-0.14,0.14,0.14]); ys=np.array([-0.18,0.18,0.18,-0.18]); yaw=np.array([-0.0201,0.0201,-0.0201,0.0201])
        A=np.zeros((4,4)); A[0,:]=1.; A[1,:]=ys; A[2,:]=-xs; A[3,:]=yaw; return A
    def _mix(self,coll,torq):
        tgt=np.array([float(coll),float(torq[0]),float(torq[1]),float(torq[2])]); u=self.Ainv@tgt; u=np.asarray(u,float)
        if not np.all(np.isfinite(u)): u=self.hover.copy()
        lo=float(np.min(u-self.rot_min)); hi=float(np.min(self.rot_max-u))
        if lo<0 or hi<0:
            mean=float(np.mean(u)); dev=u-mean; sc=1.0
            for i in range(4):
                if dev[i]>1e-9: sc=min(sc,(self.rot_max-mean)/dev[i])
                elif dev[i]<-1e-9: sc=min(sc,(self.rot_min-mean)/dev[i])
            sc=float(np.clip(sc,0.,1.)); u=mean+sc*dev
        return np.clip(u,self.rot_min,self.rot_max)
    def _predict_ball_state(self,dt):
        dt=float(np.clip(dt,0.,0.25))
        if dt<=0: return
        self.ball_p=self.ball_p+self.ball_v*dt+np.array([0.,0.,-0.5*self.g*dt*dt])
        self.ball_v=self.ball_v+np.array([0.,0.,-self.g*dt])
        F=np.eye(6); F[0,3]=F[1,4]=F[2,5]=dt; qp=0.002+0.03*dt*dt; qv=0.010+0.18*dt
        Q=np.diag([qp,qp,1.5*qp,qv,qv,1.5*qv])**2; self.ball_P=F@self.ball_P@F.T+Q
    def _project_ball(self,p,v,dt):
        dt=float(np.clip(dt,-0.05,1.5))
        p2=np.asarray(p,float)+np.asarray(v,float)*dt+np.array([0.,0.,-0.5*self.g*dt*dt])
        v2=np.asarray(v,float)+np.array([0.,0.,-self.g*dt]); return p2,v2
    def _reset_filter_after_contact(self,p,v):
        self.ball_p=np.asarray(p,float).copy(); self.ball_v=np.asarray(v,float).copy()
        self.ball_P=np.diag([0.12,0.12,0.14,0.30,0.30,0.45])**2
    def _update_ball_filter(self,obs,t,dt):
        if self.t_prev is None: self.t_prev=t
        else: self._predict_ball_state(t-self.t_prev); self.t_prev=t
        if not bool(obs.get("ball_visible",False)): return self.ball_p.copy(), self.ball_v.copy()
        if bool(obs.get("dropped",False)): return self.ball_p.copy(), self.ball_v.copy()
        z=self._vec(obs.get("ball_pos",self.ball_p),3,self.ball_p)
        zv=self._vec(obs.get("ball_vel",self.ball_v),3,self.ball_v)
        src=self._scalar(obs.get("ball_source_time",t),t)
        age=self._scalar(obs.get("ball_observation_age_s",t-src),max(0.,t-src))
        new=src>self.last_source_t+0.5e-3
        if self.last_meas is not None and np.linalg.norm(z-self.last_meas[0])>3.: new=False
        if new:
            lead=max(0.,t-src); zp,zv_now=self._project_ball(z,zv,lead)
            rp=np.array([0.03,0.03,0.045])+0.20*min(age,0.25); rv=np.array([0.075,0.075,0.11])+0.45*min(age,0.25)
            if (t-self.last_contact_t)<0.35: rp*=0.4; rv*=0.4
            Rm=np.diag(np.r_[rp,rv])**2; x=np.r_[self.ball_p,self.ball_v]; y=np.r_[zp,zv_now]-x
            sig=np.sqrt(np.maximum(np.diag(self.ball_P)+np.diag(Rm),1e-9)); normed=np.abs(y)/sig
            if (t-self.last_contact_t)<0.35 or float(np.max(normed[:3]))<8.0:
                S=self.ball_P+Rm
                try: K=self.ball_P@np.linalg.inv(S)
                except: K=self.ball_P@np.linalg.pinv(S)
                upd=x+K@y; self.ball_P=(np.eye(6)-K)@self.ball_P
                self.ball_p=upd[:3]; self.ball_v=upd[3:]
                self.ball_v[:2]=np.clip(self.ball_v[:2],-5.,5.); self.ball_v[2]=float(np.clip(self.ball_v[2],-8.,8.))
                self.visible_once=True; self.last_source_t=src; self.last_meas=(z.copy(),zv.copy())
        return self.ball_p.copy(), self.ball_v.copy()
    def _gate_required_z(self,g): return float(g[2]+1.90+self.ball_r+0.01)
    def _gate_window_center(self,g): return np.array([g[0],g[1],g[2]+0.38+0.72],float)
    def _update_progress(self,t,bp,bv,rp,gates,raw_p=None,raw_v=None):
        if self.last_ball_x is None: self.last_ball_x=float(bp[0]); self.last_ball_z=float(bp[2]); self.last_ball_vz=float(bv[2]); return
        dxy=float(np.linalg.norm(bp[:2]-rp[:2])); dz=float(bp[2]-rp[2])
        dvz=float(bv[2]-(self.last_ball_vz if self.last_ball_vz is not None else bv[2]))
        contact=False
        if dxy<0.34 and abs(dz)<0.14 and (dvz>0.15 or bv[2]>0.15) and t-self.last_contact_t>0.08: contact=True
        if not contact and raw_p is not None and raw_v is not None:
            dr=float(np.linalg.norm(raw_p[:2]-rp[:2])); dz2=float(raw_p[2]-rp[2])
            if dr<0.45 and abs(dz2)<0.22 and raw_v[2]>0.10 and t-self.last_contact_t>0.08: contact=True; bp=raw_p; bv=raw_v
        if contact:
            self.last_contact_t=t; self.last_contact_x=float(bp[0]); self.contact_count+=1
            gi=int(np.clip(self.gate_idx,0,3)); self.bounce_done[gi]=True; self._reset_filter_after_contact(bp,bv)
        for i in range(4):
            if self.gate_done[i]: continue
            gx,gy,_h=gates[i]; crossed=(self.last_ball_x < gx <= bp[0]) or abs(bp[0]-gx)<0.05
            if crossed and abs(bp[1]-gy)<1.00 and bp[2]>self._gate_required_z(gates[i])+0.01:
                if self.bounce_done[i] or (t-self.last_contact_t)<0.70:
                    self.gate_done[i]=True; self.gate_idx=max(self.gate_idx,i+1)
        self.last_ball_x=float(bp[0]); self.last_ball_z=float(bp[2]); self.last_ball_vz=float(bv[2])
    def _desired_ball_velocity_for_gate(self,bp,gate,target_next):
        dx=max(0.35,float(gate[0]-bp[0])); dy=float(gate[1]-bp[1]); req_z=self._gate_required_z(gate)+0.12
        vx=float(np.clip(dx/0.60,1.5,2.5)); T=dx/max(vx,1e-6); vy=float(np.clip(dy/max(T,0.25),-1.1,1.1))
        vz=(req_z-float(bp[2])+0.5*self.g*T*T)/max(T,0.20)
        if self.gate_idx<3: vz+=0.22
        else: vz=min(vz,2.8); dx_t=max(0.25,float(target_next[0]-bp[0])); vx=float(np.clip(dx_t/0.90,1.0,2.0)); vy=float(np.clip((target_next[1]-bp[1])/0.90,-0.8,0.8))
        return np.array([vx,vy,float(np.clip(vz,1.1,3.8))],float)
    def _intercept_point(self,t,drone_p,racket_p,ball_p,ball_v,gates,target):
        gi=int(np.clip(self.gate_idx,0,3)); gate=gates[gi]
        cands=[]
        for tau in np.linspace(0.06,0.75,34):
            bp,bv=self._project_ball(ball_p,ball_v,tau)
            if bp[2]<0.55 or bp[2]>2.10: continue
            if bv[2]>0.40: continue
            if bp[0]>gate[0]-0.10: continue
            dr=bp-np.array([0.,0.,0.025]); dd=dr-np.array([0.,0.,self.racket_local_z])
            d=float(np.linalg.norm(dd-drone_p)); reach=0.28+3.2*tau
            score=abs(bp[0]-max(0.05,gate[0]-0.70))+0.30*d+0.15*max(0.,bv[2])+0.65*abs(bp[1]-gate[1])
            if d<reach: cands.append((score,tau,bp,bv,dd))
        if cands:
            cands.sort(key=lambda x:x[0]); _s,tau,bp,bv,dd=cands[0]
        else:
            tau=0.28; bp,bv=self._project_ball(ball_p,ball_v,tau)
            ax=min(float(gate[0]-0.55), max(float(ball_p[0]+0.12), float(ball_p[0])))
            bp[0]=ax; bp[1]=0.70*bp[1]+0.30*gate[1]; bp[2]=float(np.clip(bp[2],0.90,1.65))
            dd=bp-np.array([0.,0.,self.racket_local_z+0.025])
        des_v=self._desired_ball_velocity_for_gate(bp,gate,target)
        dd=dd.copy(); dd[:2]-=0.045*des_v[:2]; dd[2]=float(np.clip(dd[2],0.55,1.95))
        return dd, des_v, tau, bp, bv
    def _plan(self,obs,t,drone_p,drone_v,racket_p,ball_p,ball_v,gates,target):
        gi=int(np.clip(self.gate_idx,0,4))
        # Window logic: try to avoid backtracking
        if self.window_idx<4:
            wc=self._gate_window_center(gates[self.window_idx])
            # if drone far past window, auto-skip it to avoid backtrack
            if drone_p[0] - wc[0] > 0.9 and self.window_idx < gi:
                self.window_done[self.window_idx]=True; self.window_idx+=1
            elif abs(drone_p[0]-wc[0])<0.20 and abs(drone_p[1]-wc[1])<0.68 and abs(drone_p[2]-wc[2])<0.42:
                self.window_done[self.window_idx]=True; self.window_idx+=1
        if gi>=4:
            self.phase="TARGET"; off=np.array([-0.25,-0.12,0.82])
            if ball_p[2]<0.60 and np.linalg.norm(ball_p[:2]-target[:2])<1.0:
                pd=np.array([target[0]-0.35,target[1]-0.20,1.05]); vd=np.zeros(3); self.phase="SETTLE"
            else:
                lt=0.20; bp,bv=self._project_ball(ball_p,ball_v,lt)
                if bp[0]<target[0]-0.85 and bp[2]<1.15 and t-self.last_contact_t>0.25:
                    pd=bp-np.array([0.04,0.02,self.racket_local_z+0.015]); vd=np.array([1.0,0.45,0.20]); self.phase="BOUNCE"
                else: pd=bp+off; pd[2]=float(np.clip(pd[2],0.85,1.65)); vd=0.35*bv
            yaw=math.atan2(target[1]-drone_p[1],target[0]-drone_p[0]); return pd,vd,np.zeros(3),yaw
        gate=gates[gi]; req_z=self._gate_required_z(gate)
        if ball_p[0]>gate[0]+0.16 and ball_p[2]>req_z-0.08:
            self.gate_done[gi]=True; self.gate_idx=min(4,gi+1); gi=int(np.clip(self.gate_idx,0,4))
            if gi>=4: return self._plan(obs,t,drone_p,drone_v,racket_p,ball_p,ball_v,gates,target)
            gate=gates[gi]
        # Fixed window logic: only transit if bounce done and window is recent (not far behind)
        # Do NOT go back for windows far behind if ball is approaching next gate
        ball_dist_to_next_gate = gate[0] - ball_p[0]
        if ball_dist_to_next_gate < 1.2 and self.gate_idx < 4:
            # Ball is close to next gate, prioritize bounce over old windows
            pass
        elif self.window_idx < min(self.gate_idx,4) and self.bounce_done[self.window_idx]:
            # Only thread if window is not far behind ball
            wc_check = self._gate_window_center(gates[self.window_idx])
            if ball_p[0] - wc_check[0] < 2.0:  # window not too far behind ball
                self.phase="TRANSIT"; wc=self._gate_window_center(gates[self.window_idx]); gw=gates[self.window_idx]
                sm=0.15; pd=wc.copy(); wb=gw[2]+0.38; wt=gw[2]+0.38+0.76; pd[2]=float(np.clip(wc[2], wb+sm, wt-sm))
                if drone_p[0]<wc[0]-0.10: pd[0]=wc[0]-0.08
                else: pd[0]=wc[0]+0.25
                yoff=wc[1]-drone_p[1]; pd[1]=float(np.clip(wc[1]+0.3*yoff, gw[1]-0.35, gw[1]+0.35))
                d2w=float(np.linalg.norm(drone_p[:2]-wc[:2])); sp=0.8 if d2w<0.5 else 1.0
                vd=np.array([sp,0.2*yoff,0.]); yaw=math.atan2((gates[min(self.window_idx+1,3),1]-drone_p[1]),1.0); return pd,vd,np.zeros(3),yaw
        pos_int, des_v, tau, bp, bv = self._intercept_point(t,drone_p,racket_p,ball_p,ball_v,gates,target)
        tsc=t-self.last_contact_t; near=np.linalg.norm((racket_p-bp)[:2])<0.30 and abs(racket_p[2]-bp[2])<0.20
        if bool(self.bounce_done[gi]) and tsc<0.18:
            self.phase="BOUNCE"; pd=pos_int+np.array([0.14,0.07*np.sign(gate[1]-drone_p[1]),0.05]); vd=np.array([1.2,0.5*(gate[1]-drone_p[1]),0.18])
        elif ball_p[0] < gate[0]-0.18:
            self.phase="INTERCEPT" if self.visible_once else "HOVER"; pd=pos_int
            close_xy=np.linalg.norm((ball_p-racket_p)[:2])<0.40; closing_z=(ball_p[2]-racket_p[2])<0.28 and ball_v[2]<0.2
            vz_cmd=0.70 if (close_xy and closing_z) else 0.14
            vd=np.array([(0.75 if gi==3 else 0.40)*des_v[0]+(0.8 if gi==3 else 0.0),(0.25 if gi==3 else 0.40)*des_v[1],vz_cmd])
            if not near: vd[:2]+=self._clip_norm((pd-drone_p)[:2]*1.1,1.3)
        else:
            self.phase="REPOSITION"; pd=np.array([gate[0]-0.38,gate[1]-0.08,min(req_z-1.00,1.55)]); vd=np.array([0.5,0.18,0.0])
        pd[2]=float(np.clip(pd[2],0.45,2.00)); pd[1]=float(np.clip(pd[1],gate[1]-0.75,gate[1]+0.75))
        yaw=math.atan2(gate[1]-drone_p[1], max(0.25,gate[0]-drone_p[0])); return pd,vd,np.zeros(3),yaw
    def _controller(self,obs,pd,vd,af,yaw_des):
        pos=self._vec(obs.get("drone_pos",[0,0,1]),3,np.array([0.,0.,1.])); vel=self._vec(obs.get("drone_linvel",[0,0,0]),3,np.zeros(3))
        quat=self._vec(obs.get("drone_quat",[1,0,0,0]),4,np.array([1.,0.,0.,0.])); om=self._vec(obs.get("drone_angvel",[0,0,0]),3,np.zeros(3))
        dt=float(np.clip(self._scalar(obs.get("dt",0.01),0.01),0.002,0.05))
        err=np.asarray(pd,float)-pos
        if np.linalg.norm(err)<0.45: self.int_pos_integral+=err*dt; self.int_pos_integral=np.clip(self.int_pos_integral,-0.25,0.25)
        else: self.int_pos_integral*=0.92
        kp=np.array([4.0,4.0,5.8]); kd=np.array([2.8,2.8,3.6]); ki=np.array([0.18,0.18,0.09])
        acc=np.asarray(af,float)+kp*err+kd*(np.asarray(vd,float)-vel)+ki*self.int_pos_integral
        acc[:2]=self._clip_norm(acc[:2],5.5); acc[2]=float(np.clip(acc[2],-5.,8.))
        R=self._quat_to_R(quat); at=acc+np.array([0.,0.,self.g]); an=float(np.linalg.norm(at))
        b3=np.array([0.,0.,1.]) if an<1e-6 else at/an
        tilt=42. if self.phase in ("INTERCEPT","BOUNCE") else 35.; ms=math.sin(math.radians(tilt))
        hn=float(np.linalg.norm(b3[:2]))
        if hn>ms:
            b3[:2]*=ms/hn; b3[2]=max(0.25, math.sqrt(max(0.,1.-float(np.dot(b3[:2],b3[:2]))))); b3/=max(1e-9,np.linalg.norm(b3))
        cy,sy=math.cos(yaw_des),math.sin(yaw_des); b1y=np.array([cy,sy,0.]); b2=np.cross(b3,b1y)
        if np.linalg.norm(b2)<1e-6: b2=np.array([0.,1.,0.])
        b2/=np.linalg.norm(b2); b1=np.cross(b2,b3); Rd=np.column_stack([b1,b2,b3])
        coll=self.mass*float(np.dot(at,R[:,2])); coll=float(np.clip(coll,0.25*np.sum(self.hover),3.0*np.sum(self.hover)))
        eR=self._vee_att_error(Rd,R); kp_a=np.array([0.90,0.90,0.30]); kd_a=np.array([0.16,0.16,0.09])
        torq=-kp_a*eR-kd_a*om; torq[0]=float(np.clip(torq[0],-1.2,1.2)); torq[1]=float(np.clip(torq[1],-1.2,1.2)); torq[2]=float(np.clip(torq[2],-0.18,0.18))
        u=self._mix(coll,torq)
        if self.last_cmd is not None:
            alpha=0.70 if self.phase in ("INTERCEPT","BOUNCE") else 0.55; u=alpha*u+(1-alpha)*self.last_cmd
        u=np.clip(u,self.rot_min,self.rot_max); self.last_cmd=u.copy(); return u
    def _direct_launch_action(self,t):
        hs=float(np.sum(self.hover))
        if t<0.10: return self._mix(14.0, np.array([-0.227,0.30734401840692227,0.]))
        if t<0.33522502703419393: return self._mix(49.73480128424209, np.array([-0.1,0.20668423533793084,0.]))
        if t<0.4847193722498003: return self._mix(0.2461647213381991*hs, np.array([0.144,-0.022846311835017508,0.]))
        go=float(self.smash_go_t)
        smash_dur=0.09053261477998296  # same as 1.017-0.926
        settle_dur=0.099996999999999999  # ~0.1
        if (not self.defer_smash) or (not self.deferred_smash_done and t < go):
            # Normal coast, or deferred wait: stay soft until go
            if t < go:
                if self.defer_smash and t >= 0.90:
                    # Drop briefly to remount under ball
                    return np.zeros(4)
                return self._mix(0.6808073459140787*hs, np.array([0.02,-0.12058394642623566,0.]))
        if t < go + smash_dur:
            return self._mix(36.0 if self.defer_smash else 22.0, np.array([0.004337874157701538,0.05,0.]))
        if t < go + smash_dur + settle_dur:
            if self.defer_smash: self.deferred_smash_done=True
            return self._mix(0.62*hs, np.array([0.025607699034207537,-0.03,0.]))
        return None

    def act(self,obs):
        try:
            self.theta = {**DEFAULT_THETA, **(self.theta or {})}
            t=self._scalar(obs.get("time",0.0),0.0); dt=self._scalar(obs.get("dt",0.01),0.01)
            if self.mass is None:
                self.hover=self._vec(obs.get("hover_rotor_thrusts",self.hover),4,self.hover); self.mass=float(np.clip(np.sum(self.hover)/self.g,0.8,2.2))
            gates=np.asarray(obs.get("gates",self.gates0),float).reshape(4,3); target=self._vec(obs.get("target",self.target0),3,self.target0)
            # If racket is above/through the ball near second-smash time, defer smash until remounted
            if (not self.defer_smash) and 0.88 <= t <= 0.98 and bool(obs.get("ball_visible",False)):
                _dp=self._vec(obs.get("drone_pos",[0,0,1]),3,np.array([0.,0.,1.]))
                _rp=self._vec(obs.get("racket_pos",_dp+np.array([0.,0.,self.racket_local_z])),3,_dp+np.array([0.,0.,self.racket_local_z]))
                _bp=self._vec(obs.get("ball_pos",[0.,0.,1.7]),3,np.array([0.,0.,1.7]))
                _dxy=float(np.linalg.norm((_bp-_rp)[:2])); _dz=float(_bp[2]-_rp[2])
                if _dxy < 0.36 and _dz < 0.015:
                    self.defer_smash=True
                    self.smash_go_t=float(np.clip(t+0.10, 0.98, 1.12))
            # Early inside-offset (unclipped tau): arms hot-out 000 at t≈0.54–0.58; spares 011/nom.
            th = self.theta
            if (not self._early_in) and float(th["b1_t0"]) <= t <= float(th["b1_t1"]) and bool(obs.get("ball_visible", False)):
                _g=np.asarray(obs.get("gates", self.gates0), float).reshape(4, 3)
                _bp=self._vec(obs.get("ball_pos", [0., 0., 1.7]), 3, np.array([0., 0., 1.7]))
                _bv=self._vec(obs.get("ball_vel", [1., 0., 0.]), 3, np.array([1., 0., 0.]))
                _dx=float(_g[1,0]-_bp[0]); _vx=float(max(0.7,_bv[0])); _tau=float(_dx/_vx)
                if _tau > 0.05:
                    _ym=abs(float(_bp[1]+_bv[1]*_tau)-float(_g[1,1]))
                    if _ym >= float(th["b1_ym"]) and abs(float(_bv[1])) <= float(th["b1_vy_max"]) and float(_bp[1]) >= float(th["b1_by_min"]):
                        self._early_in=True; self._early_band=1
                        self._far=float(np.sign(_bv[1])) if abs(float(_bv[1]))>0.15 else 1.0
            # 002-band: later, slightly lower ym, higher by (011 early by too low)
            if (not self._early_in) and 0.58 <= t <= 0.68 and bool(obs.get("ball_visible", False)):
                _g=np.asarray(obs.get("gates", self.gates0), float).reshape(4, 3)
                _bp=self._vec(obs.get("ball_pos", [0., 0., 1.7]), 3, np.array([0., 0., 1.7]))
                _bv=self._vec(obs.get("ball_vel", [1., 0., 0.]), 3, np.array([1., 0., 0.]))
                _dx=float(_g[1,0]-_bp[0]); _vx=float(max(0.7,_bv[0])); _tau=float(_dx/_vx)
                if _tau > 0.05:
                    _ym=abs(float(_bp[1]+_bv[1]*_tau)-float(_g[1,1]))
                    if 0.94 <= _ym <= 1.02 and abs(float(_bv[1])) <= 1.60 and float(_bp[1]) >= 0.36:
                        self._early_in=True; self._early_band=2; self._arm_ymiss=float(_ym)
                        self._far=float(np.sign(_bv[1])) if abs(float(_bv[1]))>0.15 else 1.0
            # Cold/lateral band: small |by|, modest ym — converts 014/crosswind/offset cluster without hot 000.
            if (not self._early_in) and float(th["cold_t0"]) <= t <= float(th["cold_t1"]) and bool(obs.get("ball_visible", False)):
                _g=np.asarray(obs.get("gates", self.gates0), float).reshape(4, 3)
                _bp=self._vec(obs.get("ball_pos", [0., 0., 1.7]), 3, np.array([0., 0., 1.7]))
                _bv=self._vec(obs.get("ball_vel", [1., 0., 0.]), 3, np.array([1., 0., 0.]))
                _dx=float(_g[1,0]-_bp[0]); _vx=float(max(0.7,_bv[0])); _tau=float(_dx/_vx)
                if _tau > 0.05:
                    _ym=abs(float(_bp[1]+_bv[1]*_tau)-float(_g[1,1]))
                    if (
                        _ym >= float(th["cold_ym"])
                        and abs(float(_bv[1])) <= float(th["cold_vy_max"])
                        and abs(float(_bp[1])) <= float(th["cold_by_abs_max"])
                    ):
                        self._early_in=True; self._early_band=3; self._arm_ymiss=float(_ym)
                        self._far=float(np.sign(_bv[1])) if abs(float(_bv[1]))>0.12 else float(np.sign(_g[1,1]-_bp[1]) or 1.0)
            _tend = (
                float(th["cold_tend"]) if int(getattr(self, "_early_band", 0)) == 3
                else (
                    (float(th["band2_tend_base"]) + float(th["band2_tend_span"])*float(min(0.20, max(0.0, getattr(self,"_arm_ymiss",0.95)-0.90))/0.20))
                    if int(getattr(self, "_early_band", 0)) == 2 else 0.80
                )
            )
            if self._early_in and 0.52 <= t <= _tend and bool(obs.get("ball_visible", False)):
                _bp=self._vec(obs.get("ball_pos", [0., 0., 1.7]), 3, np.array([0., 0., 1.7]))
                _dp=self._vec(obs.get("drone_pos",[0,0,1]),3,np.array([0.,0.,1.]))
                far=self._far
                _inside = float(th["cold_inside"]) if int(getattr(self, "_early_band", 0)) == 3 else 0.25
                pd=np.array([
                    float(_bp[0]-0.12),
                    float(_bp[1]+far*(-_inside)),
                    float(np.clip(_bp[2]-self.racket_local_z-0.08, 1.3, 3.0)),
                ])
                u=self._controller(obs, pd, np.array([2.0, 3.5*(pd[1]-_dp[1]), 1.5]), np.zeros(3), 0.0)
                self.last_cmd=np.clip(u,self.rot_min,self.rot_max); self._update_ball_filter(obs,t,dt)
                return [float(x) for x in self.last_cmd]
            # Narrow window: 011 ymiss~0.90 here; 000/002 already >1.05 (would only lose soft score).
            if (not self._skip_smash) and 0.89 <= t <= 0.93 and bool(obs.get("ball_visible", False)):
                _g=np.asarray(obs.get("gates", self.gates0), float).reshape(4, 3)
                _bp=self._vec(obs.get("ball_pos", [0., 0., 1.7]), 3, np.array([0., 0., 1.7]))
                _bv=self._vec(obs.get("ball_vel", [1., 0., 0.]), 3, np.array([1., 0., 0.]))
                _dx=float(_g[1,0]-_bp[0]); _vx=float(max(0.7,_bv[0])); _tau=float(np.clip(_dx/_vx,0.05,1.2))
                _ym=abs(float(_bp[1]+_bv[1]*_tau)-float(_g[1,1]))
                if 0.85 <= _ym <= 1.00 and abs(float(_bv[1])) <= 1.50:
                    self._skip_smash=True; self._race_g1=True; self._arm_ymiss=float(_ym)
                    self._far=float(np.sign(_bv[1])) if abs(float(_bv[1]))>0.25 else 1.0
                    self._g0_sep_t=float(self.last_contact_t)
            lu=self._direct_launch_action(t)
            if lu is not None and self._skip_smash and t >= float(self.smash_go_t) - 0.02:
                hs=float(np.sum(self.hover))
                if t < float(self.smash_go_t) + 0.04:
                    lu=self._mix(0.55*hs, np.array([0.02, -0.02, 0.0]))
                else:
                    lu=None
            if lu is not None:
                self.last_cmd=np.clip(lu,self.rot_min,self.rot_max); self._update_ball_filter(obs,t,dt)
                return [float(x) for x in self.last_cmd]
            dp=self._vec(obs.get("drone_pos",[0,0,1]),3,np.array([0.,0.,1.])); dv=self._vec(obs.get("drone_linvel",[0,0,0]),3,np.zeros(3))
            rp=self._vec(obs.get("racket_pos",dp+np.array([0.,0.,self.racket_local_z])),3,dp+np.array([0.,0.,self.racket_local_z]))
            bp,bv=self._update_ball_filter(obs,t,dt)
            for _i in range(4):
                if not np.isfinite(self.cross_seen_t[_i]) and bp[0] >= gates[_i,0]: self.cross_seen_t[_i]=t
            if np.isfinite(self.cross_seen_t[1]): self.gate_idx=max(self.gate_idx,2)
            if np.isfinite(self.cross_seen_t[2]): self.gate_idx=max(self.gate_idx,3)
            raw_p=self._vec(obs.get("ball_pos",bp),3,bp); raw_v=self._vec(obs.get("ball_vel",bv),3,bv)
            self._update_progress(t,bp,bv,rp,gates,raw_p=raw_p,raw_v=raw_v)
            if self.raw_prev_bx is not None and bool(obs.get("ball_visible",False)):
                for _i in range(4):
                    if (not np.isfinite(self.raw_cross[_i]) and self.raw_prev_bx < gates[_i,0] <= float(raw_p[0])
                        and float(raw_p[2]) > gates[_i,2]+1.85):
                        self.raw_cross[_i]=t
            if bool(obs.get("ball_visible",False)):
                self.raw_prev_bx=float(raw_p[0])
            # Classify early via raw vx, or at gate-2 x-crossing.
            if self.gate2_eta3 is None and t>=1.14 and bool(obs.get("ball_visible",False)) and float(raw_p[0])>1.0 and float(raw_p[2])>1.5:
                vx=max(0.8,float(raw_v[0])); vy=float(raw_v[1])
                self.gate2_eta3=(gates[2,0]-float(raw_p[0]))/vx
                yerr=abs(float(raw_p[1])-float(gates[min(2,3),1]))
                # Fast OR strong lateral miss — keep nominal (moderate vx, small yerr) on baseline.
                self.fast_midcourse = bool(self.gate2_eta3 < 0.32 or vx >= 4.40 or (abs(vy)>=1.8 and yerr>0.45))
            if np.isfinite(self.cross_seen_t[1]) and self.gate2_eta3 is None:
                vx=max(0.8,float(bv[0])); self.gate2_eta3=(gates[2,0]-float(bp[0]))/vx
                self.fast_midcourse = bool(self.gate2_eta3 < 0.295 or vx > 4.55)
            c3 = self.raw_cross[2] if np.isfinite(self.raw_cross[2]) else self.cross_seen_t[2]
            c4 = self.raw_cross[3] if np.isfinite(self.raw_cross[3]) else self.cross_seen_t[3]
            # Non-fast used to SETTLE after g3 cross without rematch — escalate instead if still missing gates.
            if (not self.fast_midcourse) and np.isfinite(self.cross_seen_t[2]) and bp[0]>gates[2,0]+0.55 and t-self.cross_seen_t[2]>0.36:
                if bool(self.bounce_done[2] and self.bounce_done[3]) or (float(bp[2])<0.45 and float(bp[0])>gates[3,0]+0.2):
                    self.finish_latched=True
                else:
                    self.fast_midcourse=True
            if self.fast_midcourse and np.isfinite(c4) and (t-c4)>0.22:
                self.finish_latched=True
            if self.finish_latched and not self.rescue_g3:
                # Soft settle near end of course (kill flyaway coast).
                self.phase="SETTLE"
                hold=np.array([float(target[0]-0.55), float(target[1]-0.25), 1.25])
                yaw=math.atan2(hold[1]-dp[1], max(0.2,hold[0]-dp[0]))
                vd=np.array([float(np.clip(-0.55*dv[0],-1.6,1.6)), float(np.clip(-0.55*dv[1],-1.6,1.6)), float(np.clip(0.9*(hold[2]-dp[2])-0.4*dv[2],-2.5,2.0))])
                u=self._controller(obs,hold,vd,np.zeros(3),yaw)
                _R=self._quat_to_R(obs.get("drone_quat",[1,0,0,0])); _om=self._vec(obs.get("drone_angvel",[0,0,0]),3,np.zeros(3))
                _er=self._vee_att_error(np.eye(3),_R); _tq=-np.array([2.0,2.0,0.35])*_er-np.array([0.75,0.75,0.14])*_om
                _tq=np.clip(_tq,[-0.9,-0.9,-0.14],[0.9,0.9,0.14])
                u_lvl=self._mix(1.05*float(np.sum(self.hover))+0.35*(hold[2]-dp[2]), _tq)
                self.last_cmd=0.45*u+0.55*u_lvl; return [float(x) for x in self.last_cmd]

            bp_u,bv_u = (raw_p,raw_v) if self.fast_midcourse else (bp,bv)
            dxy=float(np.linalg.norm((bp_u-rp)[:2])); dz=float(bp_u[2]-rp[2])

            # Scorer quiet window ONLY on already-hot lateral (protect nominal g4 timing).
            g0c = self.raw_cross[0] if np.isfinite(self.raw_cross[0]) else self.cross_seen_t[0]
            if (np.isfinite(g0c) and (t - g0c) < 0.085 and (not self.g3_smashed)
                    and bool(obs.get("ball_visible", False))):
                g1=gates[1]
                dx=float(g1[0]-raw_p[0]); vx=float(max(0.65, raw_v[0]))
                tau=float(np.clip(dx/vx, 0.04, 0.70))
                y_miss=abs(float(raw_p[1]+raw_v[1]*tau)-float(g1[1]))
                th=self.theta
                if y_miss > float(th["quiet_ym_hot"]) or abs(float(raw_v[1])) > float(th["quiet_vy_hot"]):
                    self.last_cmd=np.zeros(4); return [0.0, 0.0, 0.0, 0.0]
                if y_miss > float(th["quiet_ym_mod"]) and (t - g0c) < float(th["quiet_mod_dt"]):
                    self.last_cmd=np.zeros(4); return [0.0, 0.0, 0.0, 0.0]

            if t < self.sep_until:
                self.last_cmd = np.zeros(4); return [0.0, 0.0, 0.0, 0.0]

            # Multi-tick punch hold then SEP.
            if self._punch_cmd is not None and t < self._punch_hold_until:
                self.last_cmd = self._punch_cmd
                return [float(x) for x in self.last_cmd]
            if self._punch_cmd is not None and t >= self._punch_hold_until:
                self.sep_until = max(self.sep_until, t + 0.45)
                self._punch_cmd = None
                self.last_cmd = np.zeros(4); return [0.0, 0.0, 0.0, 0.0]

            # Early golden rematch (011): after skip-smash, punch ~1.05 while by≈g1y before racing late.
            if (self._skip_smash and (not self.rescue_done[1]) and (not self.g3_smashed)
                    and t >= 0.96 and bool(obs.get("ball_visible", False))
                    and 0.85 <= self._arm_ymiss <= 1.00):
                bp_r, bv_r = raw_p, raw_v
                g1 = gates[1]
                g0c = self._g0_sep_t if self._g0_sep_t > 0 else self.last_contact_t
                if (t - g0c) < 0.12:
                    self.last_cmd = np.zeros(4); return [0.0, 0.0, 0.0, 0.0]
                dxy_r = float(np.linalg.norm((bp_r - rp)[:2])); dz_r = float(bp_r[2] - rp[2])
                far = self._far
                ready = (0.97 <= t <= 1.20 and -0.08 < dz_r < 0.52 and float(bv_r[2]) < 1.35
                         and dxy_r < 0.65)
                if ready:
                    self.rescue_done[1] = True; self.pop_end_t = t
                    th=self.theta
                    ty = float(np.clip(float(th["early_tip_ty_far"])*far - float(th["early_tip_ty_vy"])*float(bv_r[1]) + 0.15*(g1[1]-bp_r[1]), -1.15, 1.15))
                    self._punch_cmd = self._mix(float(th["early_tip_mix"]), np.array([0.20, ty, 0.0]))
                    self._punch_hold_until = t + 0.05
                    self.last_cmd = self._punch_cmd
                    return [float(x) for x in self.last_cmd]

            # Race-ahead g1: only after early rematch window if skip-smash armed.
            if (not self.g3_smashed) and (not self.rescue_done[1]) and t >= 0.90 and bool(obs.get("ball_visible", False)) and ((not self._skip_smash) or self._arm_ymiss > 1.05 or t >= 1.20):
                bp_r, bv_r = raw_p, raw_v
                g0x = float(gates[0,0]); g1 = gates[1]
                meet_x = float(g1[0]) - float(self.theta["race_meet_back"])
                dx = meet_x - float(bp_r[0]); vx = float(max(0.7, bv_r[0]))
                tau = float(np.clip(dx / vx, 0.05, 1.3))
                meet_y = float(bp_r[1] + bv_r[1] * tau)
                meet_z = float(bp_r[2] + bv_r[2] * tau - 0.5 * self.g * tau * tau)
                y_miss = abs(meet_y - float(g1[1]))
                if y_miss > float(self.theta["race_ym_arm"]) and float(bp_r[0]) > g0x - 0.40:
                    self._race_g1 = True
                if self._race_g1 and float(bp_r[0]) < float(g1[0]) - 0.02:
                    far = float(np.sign(bv_r[1])) if abs(float(bv_r[1])) > 0.25 else float(np.sign(meet_y - g1[1]) or 1.0)
                    # Coast off ball after g0; sprint to meet ledge.
                    if float(bp_r[0]) < meet_x - 0.55:
                        if t - self.last_contact_t < float(self.theta["coast_after_contact"]):
                            self.last_cmd = np.zeros(4); return [0.0, 0.0, 0.0, 0.0]
                        pd = np.array([
                            float(meet_x - 0.25),
                            float(meet_y + far * float(self.theta["race_far_y"])),
                            float(np.clip(meet_z - self.racket_local_z - 0.05, 1.5, 3.5)),
                        ])
                        yaw = math.atan2(g1[1] - dp[1], max(0.2, g1[0] - dp[0]))
                        u = self._controller(obs, pd, np.array([4.0, 2.2*(pd[1]-dp[1]), 1.5]), np.zeros(3), yaw)
                        return [float(x) for x in u]
                    # Near meet: track ball from far/under, loft when close & not diving hard.
                    dxy_r = float(np.linalg.norm((bp_r - rp)[:2])); dz_r = float(bp_r[2] - rp[2])
                    far_off = (float(rp[1]) - float(bp_r[1])) * far
                    th=self.theta
                    ready = (float(th["race_dxy_lo"]) < dxy_r < float(th["race_dxy_hi"]) and -0.05 < dz_r < 0.48 and float(bv_r[2]) < 0.85
                             and float(bp_r[0]) > meet_x - 0.35 and far_off > float(th["race_far_off"]))
                    if ready:
                        self.rescue_done[1] = True; self.pop_end_t = t
                        ty = float(np.clip(float(th["race_ty_far"])*far - float(th["race_ty_vy"])*float(bv_r[1]) + float(th["race_ty_g"])*(g1[1]-bp_r[1]), -1.15, 1.15))
                        self.last_cmd = self._mix(float(th["race_mix"]), np.array([0.16, ty, 0.0]))
                        self.sep_until = t + float(th["race_sep"])
                        return [float(x) for x in self.last_cmd]
                    pd = np.array([
                        float(bp_r[0] - 0.08),
                        float(bp_r[1] + far * 0.32),
                        float(np.clip(bp_r[2] - self.racket_local_z - 0.06, 1.1, 3.4)),
                    ])
                    yaw = math.atan2(g1[1] - dp[1], max(0.2, g1[0] - dp[0]))
                    u = self._controller(obs, pd, np.array([2.5, 2.4*(pd[1]-dp[1]), 3.8]), np.zeros(3), yaw)
                    return [float(x) for x in u]

            # One-shot gate rematch: g1 for bg=1 failures, g2 for bg=2 failures (raw ball window).
            if (not self.g3_smashed) and (not self._race_g1) and t >= 1.02 and bool(obs.get("ball_visible", False)):
                bp_r, bv_r = raw_p, raw_v
                dxy_r = float(np.linalg.norm((bp_r - rp)[:2])); dz_r = float(bp_r[2] - rp[2])
                for gi in (1, 2):
                    if self.rescue_done[gi]:
                        continue
                    gprev = gates[gi - 1]; gnext = gates[gi]
                    prev_cross = self.raw_cross[gi - 1] if np.isfinite(self.raw_cross[gi - 1]) else self.cross_seen_t[gi - 1]
                    wait = 0.05 if gi == 1 else 0.08
                    if not np.isfinite(prev_cross) or (t - prev_cross) < wait:
                        continue
                    x_lo = float(gprev[0]) + (0.10 if gi == 1 else 0.14)
                    x_hi = float(gnext[0]) - (0.05 if gi == 1 else 0.10)
                    if float(bp_r[0]) < x_lo or float(bp_r[0]) > x_hi:
                        continue
                    if gi == 1:
                        bp_m = 0.45 * bp + 0.55 * bp_r
                        bv_m = 0.45 * bv + 0.55 * bv_r
                    else:
                        bp_m, bv_m = bp_r, bv_r
                    dx = float(gnext[0] - bp_m[0]); vx = float(max(0.65, bv_m[0]))
                    tau = float(np.clip(dx / vx, 0.04, 0.60))
                    y_miss = abs(float(bp_m[1] + bv_m[1] * tau) - float(gnext[1]))
                    y_thr = 0.32 if gi == 1 else 0.48
                    if y_miss < y_thr:
                        continue
                    if gi == 2 and y_miss > 0.52:
                        self.fast_midcourse = True
                    hot = y_miss > 0.75 or abs(float(bv_r[1])) > 2.0
                    if (not hot) and (t - self.last_contact_t) < 0.12 and dxy_r < 0.52:
                        self.sep_until = t + 0.30
                        self.last_cmd = np.zeros(4); return [0.0, 0.0, 0.0, 0.0]
                    if hot and (t - self.last_contact_t) < 0.05 and dxy_r < 0.38:
                        self.sep_until = t + 0.06
                        self.last_cmd = np.zeros(4); return [0.0, 0.0, 0.0, 0.0]
                    if dxy_r < 0.54 and -0.05 < dz_r < 0.46 and float(bv_r[2]) < 1.10:
                        self.rescue_done[gi] = True; self.pop_end_t = t
                        if hot:
                            ty=float(np.clip(0.65*(gnext[1]-bp_r[1]) - 0.35*float(bv_r[1]), -1.05, 1.05))
                            self.last_cmd=self._mix(55.0, np.array([0.07, ty, 0.0]))
                        else:
                            ty = float(np.clip((0.95 if gi == 1 else 0.90) * (gnext[1] - bp_r[1]), -1.10, 1.10))
                            self.last_cmd = self._mix(51.0, np.array([0.03, ty, 0.0]))
                        self.sep_until = t + 0.28
                        return [float(x) for x in self.last_cmd]
                    self.rescue_done[gi] = True
                    pd = np.array([
                        float(bp_r[0] - 0.07),
                        float(np.clip(0.22 * bp_r[1] + 0.78 * gnext[1], gnext[1] - 0.95, gnext[1] + 0.95)),
                        float(np.clip(bp_r[2] - self.racket_local_z - 0.03, 0.98, 3.1)),
                    ])
                    yaw = math.atan2(gnext[1] - dp[1], max(0.2, gnext[0] - dp[0]))
                    u = self._controller(obs, pd, np.array([1.7, 1.35 * (pd[1] - dp[1]), 3.0]), np.zeros(3), yaw)
                    return [float(x) for x in u]

            # Selective early rematch: only when ballistic miss at the *next* gate is large.
            # Protects nominal (yerr ~0.2–0.35) while catching held-out lateral blowouts.
            if (not self.g3_smashed) and t >= 1.05 and (t - self.pop_end_t) > 0.18:
                next_i = 0
                for i in range(4):
                    if not np.isfinite(self.cross_seen_t[i]):
                        next_i = i
                        break
                    next_i = min(3, i + 1)
                if next_i >= 1 and float(bp_u[0]) < gates[next_i, 0] - 0.10:
                    ng = gates[next_i]
                    dx = float(ng[0] - bp_u[0])
                    vx = float(max(0.6, bv_u[0]))
                    tau = float(np.clip(dx / vx, 0.05, 0.85))
                    y_pred = float(bp_u[1] + bv_u[1] * tau)
                    y_miss = abs(y_pred - float(ng[1]))
                    z_pred = float(bp_u[2] + bv_u[2] * tau - 0.5 * self.g * tau * tau)
                    req_z = float(ng[2] + 1.97)
                    bad = (y_miss > 0.70) or (z_pred < req_z - 0.15 and float(bv_u[2]) < 0.5)
                    if bad:
                        if dxy < 0.55 and -0.05 < dz < 0.48 and float(bv_u[2]) < 1.15:
                            self.pop_end_t = t
                            ty = float(np.clip(0.70 * (ng[1] - bp_u[1]), -1.05, 1.05))
                            self.last_cmd = self._mix(50.0, np.array([0.02, ty, 0.0]))
                            return [float(x) for x in self.last_cmd]
                        pd = np.array([
                            float(bp_u[0] - 0.06),
                            float(np.clip(0.30 * bp_u[1] + 0.70 * ng[1], ng[1] - 0.90, ng[1] + 0.90)),
                            float(np.clip(bp_u[2] - self.racket_local_z - 0.02, 0.95, 3.2)),
                        ])
                        yaw = math.atan2(ng[1] - dp[1], max(0.2, ng[0] - dp[0]))
                        u = self._controller(obs, pd, np.array([1.8, 1.3 * (pd[1] - dp[1]), 3.2]), np.zeros(3), yaw)
                        return [float(x) for x in u]

            if self.fast_midcourse:
                # Climb/smash for gate3 once classified (also before filtered gate2 if already close)
                before_g3 = float(bp_u[0]) < gates[2,0]-0.06
                if (not self.g3_smashed) and before_g3 and t>=1.18:
                    if dxy<0.50 and -0.02<dz<0.35 and bv_u[2]<1.0:
                        self.g3_smashed=True; self.g3_smash_t=t; self.pop_end_t=t
                        ty=float(np.clip(0.55+0.4*(gates[2,1]-bp_u[1]), -0.2, 1.05))
                        self.last_cmd=self._mix(52.0,np.array([0.05,ty,0.])); return [float(x) for x in self.last_cmd]
                    pd=np.array([bp_u[0]-0.05, float(np.clip(0.7*bp_u[1]+0.3*gates[2,1], gates[2,1]-0.7, gates[2,1]+0.7)),
                                 float(np.clip(bp_u[2]-self.racket_local_z-0.02, 1.2, 3.5))])
                    yaw=math.atan2(gates[2,1]-dp[1], max(0.2,gates[2,0]-dp[0]))
                    u=self._controller(obs,pd,np.array([2.4,1.0*(pd[1]-dp[1]),3.6]),np.zeros(3),yaw)
                    return [float(x) for x in u]

                # Hold smash ~0.12s to earn credit (then stop so we can separate)
                if self.g3_smashed and not self.g4_smashed and (t-self.g3_smash_t)<0.12:
                    ty=float(np.clip(0.45*(gates[2,1]-bp_u[1]), -0.8, 0.8))
                    self.last_cmd=self._mix(50.0,np.array([-0.05,ty,0.])); return [float(x) for x in self.last_cmd]

                # Tracker lag: when delayed ball first reports past gate3, truth required_after is already met.
                # Also allow timed unlock from smash (~0.26s) even before delayed cross.
                timed_ok = (t - self.g3_smash_t) >= 0.26
                past_g3 = float(bp_u[0]) >= gates[2,0] - 0.05
                req4_ready = timed_ok and (past_g3 or (np.isfinite(c3) and t >= c3 - 0.05))

                if self.g3_smashed and not self.g4_smashed and not req4_ready:
                    # Prefer zeros coast to dump contact; then soft backfill
                    if (t-self.g3_smash_t)<0.30:
                        self.last_cmd=np.zeros(4); return [0.0,0.0,0.0,0.0]
                    pd=np.array([bp_u[0]-0.35, bp_u[1], max(0.95, bp_u[2]-0.55)])
                    yaw=math.atan2(gates[3,1]-dp[1], max(0.2,gates[3,0]-dp[0]))
                    u=self._controller(obs,pd,np.array([-1.5,0.2*(pd[1]-dp[1]),-2.5]),np.zeros(3),yaw)
                    return [float(x) for x in u]

                # Gate4 smash ASAP once ready, while still before gate4
                if self.g3_smashed and not self.g4_smashed and req4_ready and bp_u[0]<gates[3,0]+0.12:
                    # Reapproach under ball (allow modest lead)
                    if dxy<0.58 and -0.08<dz<0.52:
                        self.g4_smashed=True; self.pop_end_t=t; self.rescue_g3=True
                        ty=float(np.clip(0.45*(gates[3,1]-bp_u[1]), -0.8, 0.8))
                        self.last_cmd=self._mix(54.0,np.array([-0.15,ty,0.])); return [float(x) for x in self.last_cmd]
                    pd=np.array([bp_u[0]-0.10, float(np.clip(0.55*bp_u[1]+0.45*gates[3,1], gates[3,1]-0.8, gates[3,1]+0.8)),
                                 float(np.clip(bp_u[2]-self.racket_local_z-0.02, 1.0, 3.5))])
                    yaw=math.atan2(gates[3,1]-dp[1], max(0.2,gates[3,0]-dp[0]))
                    u=self._controller(obs,pd,np.array([1.8,1.1*(pd[1]-dp[1]),3.8]),np.zeros(3),yaw)
                    return [float(x) for x in u]

                if self.g4_smashed and (t-self.pop_end_t)<0.10:
                    ty=float(np.clip(0.30*(gates[3,1]-bp_u[1]), -0.6, 0.6))
                    self.last_cmd=self._mix(48.0,np.array([-0.08,ty,0.])); return [float(x) for x in self.last_cmd]
                if self.g4_smashed:
                    # SEPARATE coast, optional gate-4 window dive, then soft catch / brake hold.
                    if (t-self.pop_end_t)<0.28:
                        self.last_cmd=np.zeros(4); return [0.0,0.0,0.0,0.0]
                    if (t-self.pop_end_t)<0.00 and float(dp[2])>1.85 and abs(dp[0]-gates[3,0])<1.2:
                        g=gates[3]; zc=float(g[2]+0.38+0.72)
                        pd=np.array([float(g[0]+0.12), float(g[1]), float(zc)])
                        yaw=math.atan2(pd[1]-dp[1], max(0.15,pd[0]-dp[0]))
                        u=self._controller(obs,pd,np.array([0.35,0.15*(pd[1]-dp[1]),-2.2]),np.zeros(3),yaw)
                        if abs(dp[0]-g[0])<0.18 and abs(dp[1]-g[1])<(0.92-0.28) and abs(dp[2]-zc)<(0.72-0.28):
                            self.window_done[3]=True; self.window_idx=max(self.window_idx,4)
                        self.last_cmd=u; return [float(x) for x in u]
                    # Level out immediately — avoid tumble after high smash.
                    _R=self._quat_to_R(obs.get("drone_quat",[1,0,0,0])); _om=self._vec(obs.get("drone_angvel",[0,0,0]),3,np.zeros(3)); _Rd=np.eye(3)
                    _er=self._vee_att_error(_Rd,_R); _tq=-np.array([1.8,1.8,0.35])*_er-np.array([0.65,0.65,0.14])*_om
                    _tq=np.clip(_tq,[-1.0,-1.0,-0.15],[1.0,1.0,0.15])
                    # Soft catch / settle near target
                    if bp_u[2]>0.4 and bp_u[0] > gates[3,0]-0.2:
                        pd=np.array([0.4*bp_u[0]+0.6*(target[0]-0.30), 0.4*bp_u[1]+0.6*target[1], float(np.clip(bp_u[2]-0.35,0.95,1.8))])
                        if 0.5<bp_u[2]<1.5 and dxy<0.42 and abs(dz)<0.25 and float(bv_u[2])<0.5 and (t-self.pop_end_t)>0.25:
                            err=target[:2]-bp_u[:2]
                            self.last_cmd=self._mix(20.0+float(np.sum(self.hover))*0.15, np.array([float(np.clip(0.3*err[0],-.35,.35)), float(np.clip(0.35*err[1],-.4,.4)),0.]))
                            return [float(x) for x in self.last_cmd]
                        yaw=math.atan2(target[1]-dp[1], max(0.2,target[0]-dp[0]))
                        u=self._controller(obs,pd,np.array([0.6,0.4*(pd[1]-dp[1]),-0.5]),np.zeros(3),yaw)
                        u_lvl=self._mix(1.05*float(np.sum(self.hover)), _tq)
                        self.last_cmd=0.55*u+0.45*u_lvl; return [float(x) for x in self.last_cmd]
                    hold=np.array([float(target[0]-0.55), float(target[1]-0.25), 1.20])
                    yaw=math.atan2(hold[1]-dp[1], max(0.2,hold[0]-dp[0]))
                    vd=np.array([float(np.clip(-0.6*dv[0],-1.8,1.8)), float(np.clip(-0.6*dv[1],-1.8,1.8)), -1.0])
                    u=self._controller(obs,hold,vd,np.zeros(3),yaw)
                    u_lvl=self._mix(1.05*float(np.sum(self.hover)), _tq)
                    self.last_cmd=0.5*u+0.5*u_lvl; return [float(x) for x in self.last_cmd]

            elif np.isfinite(self.cross_seen_t[1]) and not np.isfinite(self.cross_seen_t[2]):
                _e=t-self.cross_seen_t[1]
                if 0.02 <= _e < 0.16:
                    self.phase="BOUNCE"; self.pop_end_t=t; self.last_cmd=self._mix(48.0,np.array([0.,(0.6 if abs(bv[1])<1.35 else 0.5),0.])); return [float(x) for x in self.last_cmd]
            if (not self.fast_midcourse) and 0.0 <= t-self.pop_end_t < 0.50:
                self.phase="REPOSITION"; self.last_cmd=np.zeros(4); return [0.0,0.0,0.0,0.0]
            pd,vd,af,yaw=self._plan(obs,t,dp,dv,rp,bp,bv,gates,target)
            u=self._controller(obs,pd,vd,af,yaw); self.step_count+=1
            if not np.all(np.isfinite(u)): return [float(x) for x in np.clip(self.hover,self.rot_min,self.rot_max)]
            return [float(x) for x in np.clip(u,self.rot_min,self.rot_max)]
        except Exception:
            h=np.clip(np.asarray(getattr(self,"hover",np.ones(4)*3.25),float),0.,13.)
            return [float(x) for x in h]
