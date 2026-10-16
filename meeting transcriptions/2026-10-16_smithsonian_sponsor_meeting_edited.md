# Pollen grain detection and classification model improvements with Dr. Romero

**Date:** October 16, 2026
**Meeting participant listed in source:** Yunfan Bao

## Transcript

**Yeon Ju Kim:** Hello. Alan, could you share the slide for us, please? Uh,

**Alan Yang:** yeah, sure. Thank you.

**Yun-Ying Tsai:** Hello, Dr. Romero. And is Dr. Wing going to join us? I don't

**Dr. Romero:** think so. Hi everyone. I don't think so because he's traveling and he's in California. So I think this week he will skip it.

**Them:** Okay, and I think Patrick not joining me he has an

**Yun-Ying Tsai:** I don't need to start can you share the screen with the progress?

**Dr. Romero:** will be okay to record the meeting?

**Yun-Ying Tsai:** Yeah. Maybe for the

**Dr. Romero:** ones that are missing it.

**Yun-Ying Tsai:** recording in progress. Yeah, we were recording.

**Alan Yang:** Am I sharing my screen?

**Yun-Ying Tsai:** Yes. I can't tell.

**Alan Yang:** I can't tell it only here. Here we go.

**Yeon Ju Kim:** Gret could you all it's gone

**Yun-Ying Tsai:** A little slow. Granola's life social violence.

**Alan Yang:** Yeah. Yeah, no, I was just having troubles like Let's put in the bomb. Okay.

**Yun-Ying Tsai:** Good to first page back.

**Yunfan Bao:** So so I have to start now.

**Yeon Ju Kim:** Yeah, I didn't start.

**Yunfan Bao:** So hello, Dr. Romero. And I'll start our report. This week, we trained and evaluated Method A It uses one model, to find pollen and identify its type. These images show the results We got 20 out of 274 validation specimens fully correct. Most were missed. So our main challenge is finding the pollen. And and next slide, the the... Understand why so many specimens were missed we checked the training data. Over 4,000 tiles have no annotations for the categories we are focusing on. So some may still contain pollen, which the model could learn to treat as background. Next, we'll select the training tiles so missing annotations don't teach the model to ignore pollen. And that's the data side. Next, YeonJu will discuss the model side.

**Yeon Ju Kim:** Following our initial results, I want to understand why the localization recall was so low. So I tested the same trained RF-DETR model with four different confidence thresholds from 0.5 to 0.05. I use the same 274 annotated specimens from our validation set and kept the matching IoU threshold fixed at 0.5. As you can see in the graph, growing... Lowering the confidence threshold from 0.5 to 0.05, increased localization recall from about 9% to 75%. But end to end success, which means finding a and identifying its correct category only increased from above 7% to 15%. So lowering threshold also produce many more unmatched predictions. Since our annotations are incomplete, we cannot assume that all of these are false positives. You move to next slide, please? So to understand this gap, I look more closely at the reserve for Momipites. Well, the pollen cuttings in our dataset. Their 38 annotating Momipites in the evaluated set and a low confidence threshold of 0.5, the model localized 13 of them, and 12 were correctly classified. But when I lowered the threshold to 0.05, the model look 33... 32 specimens while only five were counted as correctly classified. This was unexpected because we use exactly the same train model, so I traced the predictions for the specimens that I were previous classified correctly. I found the I found that nine specimens... The correct Momipites predictions were available at the lower threshold, but the evaluation process matched those specimens with different-class predictions at the same bounding box locations. So this suggests the part of the drop in report classifications cut up short obturates cut... Comes from how predictions are vegged to ground truth annotations rather than only from the model itself. So as a next step, I plan to invest gate... Investigate duplicate predictions and refine post processing and also consider retrain the model if I needed.

**Alan Yang:** I tried taking a stab at fixing the data issue, And when I investigated, I traced that with the training labels. Around 85% of the annotated grains most training tiles had no, like, annotation or label at all. So the model was learning that the row pollen was background essentially, without any labels attached to them. So I decided to make three changes. One was labeling every grade. Well, we first have, like, all the 28 categories. And then another, like, other category for every remaining annotated green. And then number two, I rebalanced the rare classes So the rare categories are showing up four times more often in training. And then three, I used the better starting point using the last year's pollen detector. And then I tested it in two different runs, using the RF-DETR Large and RF-DETR 2XL. And then as for results, before labeling every green, like, made the biggest difference, the share of known grains went from 9% to around 67%. Then to 74% when starting from last year's detector. The momma fights improved in the same way from nine... Or 13 of 38 found, to 24 of 38. I mean,

**Them:** Founded 31 of 39. My bad.

**Alan Yang:** And then, the issue was that, like, the naming or, like, correctly, you know, naming the category was, like, wasn't as accurate. It went from 10% to 14%. So, like, the model now finds, like, the grains but still struggles with you know, classifying the results.

**Yun-Ying Tsai:** My... So this week, I connected the model that finds specimen to existing Swin Tiny model and then which identifies their types. I compare the two approaches. The first one is to use a detector. We train this semester. And images that combines details from several surface levels. The second directly reuses last semester's train detector and selects one clearest focus Both use the same classifier. On the two seventy four labels investments from our validation data, The detector we trained this semester, FalconE 22, with 20 correctly identified. The reuse detector from the 209 was 81 currently identified. So these are the or from... Results that we used Tetra previously saw more of these slides during training. So this did not yet... But this did not yet show that how well it performs on new sites. And next, I looked at what happened after the specimens were filed. Of the 209 specimens found by the detector... Last master's detector, Swin Tiny identified 81 correctly and misidentified 128 That gives us a classification accuracy of 38.8% among the specimens found. And this shows that finding a specimen and identifying its type are separate challenges. We are finding more specimens but many still receive a runtime. Next slide, please. So my next step is to investigate those identification errors I'll check whether a specimen images are clear, whether their reference labels are correct, and whether the images will consistent with those used to train the cost for These checks may... Will help us to decide whether to adjust image processing or train a classifier, and the goal is to currently identify more of the specimens we already find. And, also, right now, we're using Swin Tiny as a classifier. And Patrick already tried the DINO fast last week. So probably we are going to try another approach that use RF-DETR plus DINO as a classifier. Next one, please. And the... These slides are from Patrick and these are the answer for, I think, Dr. Romero, you guys asked about for the time for camera rankings for the fine tuned DINO. And then that's... I think that's the result from Patrick.

**Dr. Romero:** So I have some questions, especially from from the beginning. I'm I'm a little confused. Because, yes, many of the annotations don't have ID IDs per se. Because many were initially just group in very general categories that are pollen, sport, fungi, algae. However, I sent I don't know if... I I remember sending an a file. It's an Excel file or CSV. Has the categories the number of annotations that are identified by category, and that... And it has another column that says classify. And it indicates if it says only pollen, ignore. Because any annotation that is under pollen, they're going to be overwhelmingly, higher. So there is over 6,000. So do you guys... So that that Excel file in in in when you did the training, there was a way for the model to just focus on the grains that were under the 30, 30 something categories that were defined.

**Yunfan Bao:** Yeah. Yeah. We saw it. Saw the file, I think.

**Dr. Romero:** Yeah. But when when doing the training, you like, in the parameters of the training the model is not using anything that is outside of those categories for the classification. Because for what I understand at the beginning, is, like, the model is very low because many of the annotations are not classified. But that's why there is from those annotations, there is a subset that is have I... IDs and and the numbers go from I think, 80 to to 50 or 40. So it's like a more balanced dataset. Still, probably low, but that... That's why my confusion. I don't know if if that makes sense, but that's

**Yunfan Bao:** Yeah. I think what you are saying is what we should do next. Actually, we use the like, the whole region of annotations to to put into the model as training set. But that's why the the performance was not as good as we expect. So I do think your suggestion, like, is is our next step. We should only use the the the annotations which are meaning like, the the the small... A portion of annotations as with our training set.

**Dr. Romero:** Oh, okay. Yeah. And

**Yun-Ying Tsai:** also, now we're trying to use, like, the full focal point... The full picture. So I think that's also another reason that the the performance is not doing well. So think we took that like, for when Patrick was trying to use the classification, he used only the annotation ones, and the performance is doing really well. So next step, we're trying to also trying to mix the If we're using annotations only, or like, the whole ROIs areas and then to see the differences.

**Dr. Romero:** Yeah. So so even though you have access to the detection model, that the students used before, let me share my screen for a moment. Okay. So am I... Yes. I'm sharing the right... So first, this was the the file that I was talking about. I shared it at the beginning of the of the semester. In which I specify which categories to consider for the classification. So anything that is under these names or that is not, just exclude Visa K because it has too many. And maybe momma pares. Has too many maybe reduced to a 100 or less. Right? And we talked about this, I think, last week or two weeks ago. Now in relationship with the image, So for the previous semesters, what they had... Because it was more a detection model. They had... This is the full image, and they had everything inside the image. That has annotations So this probably is not the best example. Let me find another one. Okay. This is an exam. Good. So all the annotations were inside a region and all the annotations corresponded to some sort of fossil. Right? But because it was only detection it didn't matter if it was pollen spore, blah. This semester, because it was more a classification challenge, that rule of this rectangular area goes out of the window. So it cannot be included. The only things that can be include are the the annotate... The ROIs itself. Right? Because as an example, here in the coloring of the annotation, ignore. That is your... That is not is not relevant. It's like, if two palynologists analyze the sample or if I was... It's for... More for internal annotations. But here, as you can see, the dots are... There are many pollen outside of the region. Right? And that's because I was focusing specifically in find grains that apply today to x category. So so that being said, probably inside these annotations, if I open the annotations, I don't know if you can see very well, but let me organize by name. There are many that are not identified. But there are many more that already have some sort of classification. So that's why it was very important for me to specify here Please ignore these ones and only work on these ones. Otherwise, it could happen what's JiJi's guy... JiJi's show that

**Yunfan Bao:** K.

**Dr. Romero:** model is not performing well because most of the annotations don't go into the categories of of interest. Right? Or because many many annotations that are under pollen probably are many grains of this. It's just a for for this time, the target was, okay. Let's have at least 50 examples per category. Okay. Does that make Does that make sense? I don't know. Any questions? So

**Yun-Ying Tsai:** Yeah. I think that makes sense, and then that gives us some direction that helps us to increase... Like, in... Like, improve our model performance and then we'll definitely try these kind of methods for our next approach. And then yeah, I think that's that's definitely going to be a next step for us. About Bob and Yunfan and Alan, you guys follow,

**Yunfan Bao:** Yeah. I think it makes sense too. Because what we what we do now is to like, use all pollens in the region but ignore the those kind of balance. But the... Those ignored patterns may be like, as background. So what we do next is like, ignore the the whole region of those ignored polynomial I think.

**Dr. Romero:** Yes. And and if you want, I can send a the Excel. Because, yeah, the... It's it's a little different. So so I keep the the rectangular area just because we're still using it for something else. But for the classification one. Won't apply.

**Yeon Ju Kim:** Okay. Thank you. And I I think you already sent the Excel files when the start... Beginning of the semester. But just in case, could you send it again for us? Thank you. Yeah.

**Yun-Ying Tsai:** And do you does anyone has any questions And I think... Then I think that's probably for today. We'll... You, Dr. Romero, and that your your advice is very helpful, and then we'll definitely try these kind of approach to help to, improve. And then for the next next next will be... Is going to be our midterm presentation. And so... And also like, we're going to organize our code and then we're going to update the diff... The the results to you guys as soon as possible.

**Dr. Romero:** I I... Sorry. I have a question. Can I can I? Can you show me again the... I think the last two slides where there are momma parties and some of the categories. So so so this is this is the performance of the... Of one of the models. We the the... Classifying pollen grains in a slice that had were in the training. But areas that were not include. Because this seems promising.

**Yun-Ying Tsai:** This one is Patrick used the annotation and the annotation file and then he trained the the the time node classifier with these kind of annotated files not the full picture. So I think that's why the validation accuracy is really good. Because he's not... You you for our approach is that the RF-DETR needs to find the squares specimen, but he started using a already finding specimens, and then with the one with already annotated, and then train the whole model. And I think that's why the performance is doing really well. But I I do think it's a really good approach. Because that gives us that seeing that, okay, the initial accuracy of the classifier can do really well, and then so we definitely think that for now, our RF-DETR post class classifier is not working well, but we're definitely there are some ways to help improve it to achieve this kind of accuracy.

**Dr. Romero:** Okay. Yeah. Yeah. Because those resource look really good. A

**Yun-Ying Tsai:** priority. Yeah. Okay.

**Dr. Romero:** No more questions.

**Yun-Ying Tsai:** And does anyone has any question? Further? Okay. Then... How about

**Nhi Le:** for Romero? Beside of the midterm presentations, they also repair for the GitHub software for the deliver. And they this would be, like, after the midterm presentation. So they will provide you with the and the model, how they organize on there and, like, we would like to have your feedback about how convenient to use that too.

**Dr. Romero:** Okay. Sounds great. Thank you, Nhi. We did... I didn't, like, come

**Yun-Ying Tsai:** off this Thank you for reminding us. Yeah. So I think that's today's updates, and I think we're going to keep working on this and to see it out and then generate and organize a code and then yeah. It's probably at the end of this week. We're... We hope to see you next week, and we really appreciate your advice.

**Dr. Romero:** Sounds great. Thank you so much. Thank you. Have a good weekend. You too. A good weekend, Dr. Romero, and everyone. See you guys.

**Yunfan Bao:** Thank you.

**Yeon Ju Kim:** See you. See you.
