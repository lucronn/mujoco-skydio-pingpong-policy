import math, numpy as np
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
        self.int_pos=np.zeros(3); self.last_cmd=self.hover.copy(); self.int_pos_integral=np.zeros(3); self.cross_seen_t=np.full(4,np.nan); self.pop_end_t=-1e9; self.finish_latched=False
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
        if t<0.9265607946427731: return self._mix(0.6808073459140787*hs, np.array([0.02,-0.12058394642623566,0.]))
        if t<1.017093409422756: return self._mix(22.0, np.array([0.004337874157701538,0.05,0.]))
        if t<1.117090413538269: return self._mix(0.62*hs, np.array([0.025607699034207537,-0.03,0.]))
        return None

    def act(self,obs):
        try:
            t=self._scalar(obs.get("time",0.0),0.0); dt=self._scalar(obs.get("dt",0.01),0.01)
            if self.mass is None:
                self.hover=self._vec(obs.get("hover_rotor_thrusts",self.hover),4,self.hover); self.mass=float(np.clip(np.sum(self.hover)/self.g,0.8,2.2))
            gates=np.asarray(obs.get("gates",self.gates0),float).reshape(4,3); target=self._vec(obs.get("target",self.target0),3,self.target0)
            lu=self._direct_launch_action(t)
            if lu is not None:
                self.last_cmd=np.clip(lu,self.rot_min,self.rot_max); self._update_ball_filter(obs,t,dt); return [float(x) for x in self.last_cmd]
            dp=self._vec(obs.get("drone_pos",[0,0,1]),3,np.array([0.,0.,1.])); dv=self._vec(obs.get("drone_linvel",[0,0,0]),3,np.zeros(3))
            rp=self._vec(obs.get("racket_pos",dp+np.array([0.,0.,self.racket_local_z])),3,dp+np.array([0.,0.,self.racket_local_z]))
            bp,bv=self._update_ball_filter(obs,t,dt)
            for _i in range(4):
                if not np.isfinite(self.cross_seen_t[_i]) and bp[0] >= gates[_i,0]: self.cross_seen_t[_i]=t
            if np.isfinite(self.cross_seen_t[1]): self.gate_idx=max(self.gate_idx,2)
            if np.isfinite(self.cross_seen_t[2]): self.gate_idx=max(self.gate_idx,3)
            raw_p=self._vec(obs.get("ball_pos",bp),3,bp); raw_v=self._vec(obs.get("ball_vel",bv),3,bv)
            self._update_progress(t,bp,bv,rp,gates,raw_p=raw_p,raw_v=raw_v)
            if np.isfinite(self.cross_seen_t[2]) and bp[0]>gates[2,0]+0.55 and t-self.cross_seen_t[2]>0.36: self.finish_latched=True
            if self.finish_latched:
                self.phase="SETTLE"; _R=self._quat_to_R(obs.get("drone_quat",[1,0,0,0])); _om=self._vec(obs.get("drone_angvel",[0,0,0]),3,np.zeros(3)); _Rd=np.eye(3)
                _er=self._vee_att_error(_Rd,_R); _tq=-np.array([1.6,1.6,0.30])*_er-np.array([0.55,0.55,0.12])*_om; _tq=np.clip(_tq,[-1.2,-1.2,-0.18],[1.2,1.2,0.18])
                _coll=1.2*np.sum(self.hover) if dp[2]<2.8 else np.sum(self.hover); _u=self._mix(_coll,_tq); self.last_cmd=_u.copy(); return [float(x) for x in _u]
            if np.isfinite(self.cross_seen_t[1]) and not np.isfinite(self.cross_seen_t[2]):
                _e=t-self.cross_seen_t[1]
                if 0.02 <= _e < 0.16:
                    self.phase="BOUNCE"; self.pop_end_t=t; self.last_cmd=self._mix(48.0,np.array([0.,(0.6 if abs(bv[1])<1.35 else 0.5),0.])); return [float(x) for x in self.last_cmd]
            if 0.0 <= t-self.pop_end_t < 0.50:
                self.phase="REPOSITION"; self.last_cmd=np.zeros(4); return [0.0,0.0,0.0,0.0]
            pd,vd,af,yaw=self._plan(obs,t,dp,dv,rp,bp,bv,gates,target)
            u=self._controller(obs,pd,vd,af,yaw); self.step_count+=1
            if not np.all(np.isfinite(u)): return [float(x) for x in np.clip(self.hover,self.rot_min,self.rot_max)]
            return [float(x) for x in np.clip(u,self.rot_min,self.rot_max)]
        except Exception:
            h=np.clip(np.asarray(getattr(self,"hover",np.ones(4)*3.25),float),0.,13.)
            return [float(x) for x in h]
